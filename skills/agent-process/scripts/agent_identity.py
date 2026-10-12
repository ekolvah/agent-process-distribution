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
is exit 1. The token is never printed.
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
from set_status import Gh, _json, _linked_project, _repo, run_gh

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


@dataclass
class Clone:
    root: Path
    login: str
    gh: Gh
    git: Git
    make_bot: Callable[[str], Gh]
    token: str = ""
    bot: Gh = run_gh
    repo: str = ""
    bot_id: str = ""
    project: dict[str, Any] | None = None


@dataclass
class Transition:
    name: str
    lines: list[str]
    apply: Callable[[], None] | None = None  # `None`: unchanged


def _unchanged(name: str, detail: str) -> Transition:
    return Transition(name, [f"unchanged {name}: {detail}"])


def _planned(name: str, detail: str, apply: Callable[[], None]) -> Transition:
    return Transition(name, [f"planned {name}: {detail}"], apply)


def _git(c: Clone, *args: str, ok: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[str]:
    done = c.git(["git", "-C", str(c.root), *args])
    if done.returncode not in ok or done.stdout is None:
        raise RuntimeError(f"`git {' '.join(args)}` exited {done.returncode}: {done.stderr}")
    return done


def _token(gh: Gh, login: str) -> str:
    try:
        token = gh(["gh", "auth", "token", "--user", login]).strip()
    except RuntimeError as exc:
        raise Refusal(f"refused: no gh token of {login}: {exc}") from None
    if not token:
        raise Refusal(f"refused: no gh token of {login}")
    return token


def _settings(c: Clone) -> Transition:
    path = c.root / SETTINGS
    try:
        text = init._read(path)
    except init.Conflict as exc:
        raise Refusal(f"refused: {SETTINGS} {exc}") from None
    try:
        data = json.loads(text) if text is not None else {}
    except json.JSONDecodeError as exc:
        raise Refusal(f"refused: {SETTINGS} is not valid JSON ({exc.msg})") from None
    env = data.get("env", {}) if isinstance(data, dict) else None
    if not isinstance(env, dict):
        raise Refusal(f"refused: {SETTINGS} is not a JSON object with an `env` object")
    if env.get("GH_TOKEN") == c.token:
        return _unchanged("settings", f"env.GH_TOKEN of {SETTINGS} is {c.login}'s token")
    # Re-serialising is lossless only from the form written here; any other form is the person's.
    if text is not None and text != json.dumps(data, indent=2, ensure_ascii=False) + "\n":
        raise Refusal(
            f"refused: {SETTINGS} is not in the form this script writes; set `env.GH_TOKEN` to"
            f" the output of `gh auth token --user {c.login}` by hand"
        )
    updated = {**data, "env": {**env, "GH_TOKEN": c.token}}
    text_out = json.dumps(updated, indent=2, ensure_ascii=False) + "\n"
    return _planned(
        "settings",
        f"env.GH_TOKEN of {SETTINGS} set to {c.login}'s token",
        lambda: init._write(path, text_out, init._eol(path)),
    )


def _route(c: Clone) -> Transition:
    done = _git(c, "config", "--local", "--get-all", HELPER, ok=(0, 1))
    helpers = done.stdout.splitlines() if done.returncode == 0 else []
    if helpers == ROUTE:
        return _unchanged("git", f"{HELPER} routes to {ROUTE[1]}")

    def apply() -> None:
        _git(c, "config", "--local", "--replace-all", HELPER, ROUTE[0])
        _git(c, "config", "--local", "--add", HELPER, ROUTE[1])

    return _planned("git", f"{HELPER} {json.dumps(helpers)} -> {json.dumps(ROUTE)}", apply)


def _collaborator(c: Clone) -> Transition:
    read = _json(c.gh, ["gh", "api", f"repos/{c.repo}/collaborators/{c.login}/permission"])
    if read["permission"] == "admin":
        raise Refusal(
            f"refused: {c.login} is an admin of {c.repo}; the agent's identity must not be"
        )
    role = str(read["role_name"])
    if role in WRITE_ROLES:
        return _unchanged("collaborator", f"{c.login} has {role} on {c.repo}")

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

    return _planned("collaborator", f"{c.login} from {role} to write on {c.repo}", apply)


def _project(c: Clone) -> Transition:
    assert c.project is not None
    board = f"#{c.project['number']} {c.project['title']}"
    query = ["gh", "api", "graphql", "-f", f"id={c.project['id']}", "-f", f"query={CAN_UPDATE}"]
    try:
        node = _json(c.bot, query)["data"]["node"]
    except RuntimeError as exc:
        if NO_ACCESS not in str(exc):
            raise
        node = None
    if node and node.get("viewerCanUpdate") is True:
        return _unchanged("project", f"{c.login} can update {board}")
    project_id = c.project["id"]

    def apply() -> None:
        c.gh(
            ["gh", "api", "graphql", "-f", f"projectId={project_id}", "-f", f"userId={c.bot_id}"]
            + ["-f", f"query={ADD_WRITER}"]
        )

    return _planned("project", f"{c.login} writer on {board}", apply)


def _ruleset(c: Clone) -> Transition:
    want = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    action, ruleset_id, lines = plan(c.gh, c.repo, want)
    state, detail = lines[0].split(" ", 1)
    transition = Transition("ruleset", [f"{state} ruleset: {detail}", *lines[1:]])
    if action != "unchanged":

        def apply() -> None:
            # Printed at once: a created ruleset's rollback needs this id.
            print(f"wrote ruleset {write(c.gh, c.repo, ruleset_id, want)}", flush=True)

        transition.apply = apply
    return transition


def _plan(c: Clone) -> list[Transition]:
    settings, route = _settings(c), _route(c)
    return [_collaborator(c), _project(c), settings, route, _ruleset(c)]


def identity(c: Clone, *, confirm: bool) -> None:
    if _git(c, "check-ignore", "-q", SETTINGS, ok=(0, 1)).returncode != 0:
        raise Refusal(f"refused: {SETTINGS} is not git-ignored in this clone")
    c.token = _token(c.gh, c.login)
    _settings(c)  # a local refusal before any network call
    c.bot = c.make_bot(c.token)
    user = _json(c.bot, ["gh", "api", "user"])
    if user["login"] != c.login:
        raise Refusal(f"refused: the gh token of {c.login} belongs to {user['login']}")
    c.bot_id = str(user["node_id"])
    owner, name, projects = _repo(c.gh)
    c.repo = f"{owner}/{name}"
    try:
        c.project = _linked_project(owner, name, projects)
    except ValueError as exc:
        raise Refusal(f"refused: {exc}") from None
    transitions = _plan(c)
    print("\n".join(line for t in transitions for line in t.lines))
    if not confirm or all(t.apply is None for t in transitions):
        return
    for transition in transitions:
        if transition.apply is not None:
            transition.apply()
    for transition in _plan(c):
        if transition.apply is not None:
            raise RuntimeError(f"re-plan: {transition.name} is still planned")
    print("written; GH_TOKEN reaches the agent after a Claude Code restart")


def main(
    argv: list[str] | None = None,
    *,
    gh: Gh = run_gh,
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
        identity(Clone(root or Path.cwd(), ns.bot, gh, git, bot), confirm=ns.confirm)
    except Refusal as exc:
        print(exc, file=sys.stderr)
        sys.exit(2)
    except (RuntimeError, KeyError, TypeError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
