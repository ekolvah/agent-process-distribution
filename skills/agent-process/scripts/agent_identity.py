#!/usr/bin/env python3
"""Run the agent under its own GitHub identity in this clone.

Usage: agent-process agent_identity --bot <login> (--dry-run | --confirm)

Run once per repository and clone, from the consumer root, after adding the bot to `gh`
(`gh auth login -s project,workflow` as the bot, then `gh auth switch --user <you>`). The run
refuses (exit 2) before any write when `.claude/settings.local.json` is not git-ignored in this
clone or is not in the form this script writes, `gh auth token --user <login>` yields no token,
that token belongs to another login, or <login> is an admin of the repository; the local
refusals come before any network call. Then it prints one line per transition, `planned` or
`unchanged`:

- collaborator  <login> invited to the repository with write access, the invitation accepted
                with <login>'s token
- project       <login>'s writer role on the Project linked to the repository
- settings      `env.GH_TOKEN` of this clone's `.claude/settings.local.json`, every other key kept
- git           this clone's `credential.https://github.com.helper` list reset and routed to
                `gh auth git-credential`
- ruleset       `agent-process person approves` of `templates/approval_ruleset.json`, planned as
                `activate_protection.py` plans its ruleset

`--dry-run` stops there with reads only. `--confirm` performs the planned transitions, plans
again and exits 1 naming the first transition that is still planned. A `gh` or `git` failure
is exit 1. The token is never printed. The person-side `gh` calls run as `gh`'s stored active
account, never with the session's `GH_TOKEN` or `GITHUB_TOKEN`; the bot-side calls carry the
bot's token.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

import init
from activate_protection import Refusal, plan, write
from set_status import Gh, _json, _linked_project, _repo, person_gh, run_gh
from steps import Step

Git = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

SETTINGS = ".claude/settings.local.json"
HELPER = "credential.https://github.com.helper"
ROUTE = ["", "!gh auth git-credential"]  # the empty value resets the inherited helpers
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "approval_ruleset.json"
WRITE_ROLES = ("write", "maintain")
NO_ACCESS = "Could not resolve to a"  # gh's error for a node the token cannot see
CAN_UPDATE = "query($id:ID!){node(id:$id){... on ProjectV2{viewerCanUpdate}}}"
ADD_WRITER = (
    "mutation($projectId:ID!,$userId:ID!){updateProjectV2Collaborators(input:{"
    "projectId:$projectId,collaborators:[{userId:$userId,role:WRITER}]}){clientMutationId}}"
)


def bot_gh(token: str) -> Gh:
    """`gh` as the bot: its token in `GH_TOKEN`, which takes precedence over stored accounts."""
    return partial(run_gh, env={**os.environ, "GH_TOKEN": token})


@dataclass(frozen=True)
class Person:
    """The run's inputs: the clone, the bot's login, and the person's `gh` and `git`."""

    root: Path
    login: str
    gh: Gh
    git: Git


@dataclass(frozen=True)
class Clone(Person):
    """The inputs and what the preconditions resolved: the bot's token, `gh` and node id, the
    repository and its linked Project."""

    token: str
    bot: Gh
    bot_id: str
    repo: str
    project: dict[str, Any]


def _applied(write_: Callable[[], object]) -> Callable[[], bool]:
    """A `Step.apply` running `write_`."""

    def apply() -> bool:
        write_()
        return True

    return apply


def _git(p: Person, *args: str, ok: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    done = p.git(["git", "-C", str(p.root), *args])
    if done.returncode not in ok or done.stdout is None:
        raise RuntimeError(f"`git {' '.join(args)}` exited {done.returncode}: {done.stderr}")
    return done


def _token(p: Person) -> str:
    try:
        token = p.gh(["gh", "auth", "token", "--user", p.login]).strip()
    except RuntimeError as exc:
        raise Refusal(f"refused: no gh token of {p.login}: {exc}") from None
    if not token:
        raise Refusal(f"refused: no gh token of {p.login}")
    return token


def _settings(p: Person, token: str) -> Step:
    path = p.root / SETTINGS
    try:
        text, data = init._json_object(path)
    except init.Conflict as exc:
        raise Refusal(f"refused: {SETTINGS} {exc}") from None
    env = data.get("env", {})
    if not isinstance(env, dict):
        raise Refusal(f"refused: {SETTINGS} `env` is not an object")
    if env.get("GH_TOKEN") == token:
        return Step("settings", "unchanged", f"env.GH_TOKEN of {SETTINGS} is {p.login}'s token")
    if text is not None and text != init._json_text(data):
        raise Refusal(
            f"refused: {SETTINGS} is not in the form this script writes; set `env.GH_TOKEN` to"
            f" the output of `gh auth token --user {p.login}` by hand"
        )
    text_out = init._json_text({**data, "env": {**env, "GH_TOKEN": token}})
    return Step(
        "settings",
        "planned",
        f"env.GH_TOKEN of {SETTINGS} set to {p.login}'s token",
        _applied(lambda: init._write(path, text_out, init._eol(path))),
    )


def _route(c: Clone) -> Step:
    done = _git(c, "config", "--local", "--get-all", HELPER, ok=(0, 1))
    helpers = done.stdout.splitlines() if done.returncode == 0 else []
    if helpers == ROUTE:
        return Step("git", "unchanged", f"{HELPER} routes to {ROUTE[1]}")

    def apply() -> None:
        _git(c, "config", "--local", "--replace-all", HELPER, ROUTE[0])
        _git(c, "config", "--local", "--add", HELPER, ROUTE[1])

    detail = f"{HELPER} {json.dumps(helpers)} -> {json.dumps(ROUTE)}"
    return Step("git", "planned", detail, _applied(apply))


def _collaborator(c: Clone) -> Step:
    read = _json(c.gh, ["gh", "api", f"repos/{c.repo}/collaborators/{c.login}/permission"])
    if read["permission"] == "admin":
        raise Refusal(
            f"refused: {c.login} is an admin of {c.repo}; the agent's identity must not be"
        )
    role = str(read["role_name"])
    if role in WRITE_ROLES:
        return Step("collaborator", "unchanged", f"{c.login} has {role} on {c.repo}")

    def apply() -> None:
        invitations = _json(c.bot, ["gh", "api", "user/repository_invitations"])
        pending = [i for i in invitations if i["repository"]["full_name"] == c.repo]
        if not pending:
            out = c.gh(
                ["gh", "api", "-X", "PUT", f"repos/{c.repo}/collaborators/{c.login}"]
                + ["-f", "permission=push"]
            )
            # No body (204): an existing collaborator's role changed without an invitation.
            pending = [json.loads(out)] if out.strip() else []
        for invitation in pending:
            c.bot(["gh", "api", "-X", "PATCH", f"user/repository_invitations/{invitation['id']}"])

    detail = f"{c.login} from {role} to write on {c.repo}"
    return Step("collaborator", "planned", detail, _applied(apply))


def _project(c: Clone) -> Step:
    board = f"#{c.project['number']} {c.project['title']}"
    query = ["gh", "api", "graphql", "-f", f"id={c.project['id']}", "-f", f"query={CAN_UPDATE}"]
    try:
        node = _json(c.bot, query)["data"]["node"]
    except RuntimeError as exc:
        if NO_ACCESS not in str(exc):
            raise
        node = None
    if node and node.get("viewerCanUpdate") is True:
        return Step("project", "unchanged", f"{c.login} can update {board}")
    mutation = ["gh", "api", "graphql", "-f", f"projectId={c.project['id']}"]
    mutation += ["-f", f"userId={c.bot_id}", "-f", f"query={ADD_WRITER}"]
    return Step(
        "project", "planned", f"{c.login} writer on {board}", _applied(lambda: c.gh(mutation))
    )


def _ruleset(c: Clone) -> Step:
    want = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    action, ruleset_id, lines = plan(c.gh, c.repo, want)
    status = "unchanged" if action == "unchanged" else "planned"
    detail = "\n".join([lines[0].removeprefix(f"{status} "), *lines[1:]])
    if action == "unchanged":
        return Step("ruleset", status, detail)

    def apply() -> None:
        # Printed at once: a created ruleset's rollback needs this id.
        print(f"wrote ruleset {write(c.gh, c.repo, ruleset_id, want)}", flush=True)

    return Step("ruleset", status, detail, _applied(apply))


def _plan(c: Clone) -> list[Step]:
    return [_collaborator(c), _project(c), _settings(c, c.token), _route(c), _ruleset(c)]


def identity(p: Person, make_bot: Callable[[str], Gh], *, confirm: bool) -> None:
    if _git(p, "check-ignore", "-q", SETTINGS, ok=(0, 1)).returncode != 0:
        raise Refusal(f"refused: {SETTINGS} is not git-ignored in this clone")
    token = _token(p)
    _settings(p, token)  # a local refusal before any network call
    bot = make_bot(token)
    user = _json(bot, ["gh", "api", "user"])
    if user["login"] != p.login:
        raise Refusal(f"refused: the gh token of {p.login} belongs to {user['login']}")
    owner, name, projects = _repo(p.gh)
    try:
        project = _linked_project(owner, name, projects)
    except ValueError as exc:
        raise Refusal(f"refused: {exc}") from None
    bot_id, repo = str(user["node_id"]), f"{owner}/{name}"
    c = Clone(p.root, p.login, p.gh, p.git, token, bot, bot_id, repo, project)
    steps = _plan(c)
    print("\n".join(f"{s.status} {s.label}: {s.detail}" for s in steps))
    if not confirm or all(s.apply is None for s in steps):
        return
    for step in steps:
        if step.apply is not None:
            step.apply()
    for step in _plan(c):
        if step.apply is not None:
            raise RuntimeError(f"re-plan: {step.label} is still planned")
    print("written; GH_TOKEN reaches the agent after a Claude Code restart")


def main(
    argv: list[str] | None = None,
    *,
    gh: Gh = person_gh,
    bot: Callable[[str], Gh] = bot_gh,
    git: Git = init.run,
    root: Path | None = None,
) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bot", required=True, help="the agent's GitHub login")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="plan with reads only")
    mode.add_argument("--confirm", action="store_true", help="write the plan, then plan again")
    ns = parser.parse_args(argv)
    try:
        identity(Person(root or Path.cwd(), ns.bot, gh, git), bot, confirm=ns.confirm)
    except Refusal as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
    except (RuntimeError, KeyError, TypeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
