"""The post-merge steps of `init.py` (design D1-D6 of init-runs-post-merge-steps); not a
command. Once the installation PR reads `MERGED`, a confirmed run writes `protection`, then,
with an agent account, `agent-collaborator`, `agent-project`, `approval-ruleset` and
`auto-merge`; before the merge each one not `unchanged` reads `after-merge`. The person's
calls run without `GH_TOKEN` and `GITHUB_TOKEN`; the agent's token goes only into the
`GH_TOKEN` of its own calls, never into a line or a file. The
agent account is the one github.com login of `gh auth status` that is not active, or the one
`--agent` names among several."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable

import activate_protection
import manual
from set_status import _json, person_env
from steps import InstallError, Step

APPROVAL = Path(__file__).resolve().parent.parent / "templates" / "approval_ruleset.json"
AGENT_READ = "viewer{id} repository(owner:$owner,name:$name){viewerPermission}"
PROJECT_READ = (
    "repositoryOwner(login:$owner){... on ProjectV2Owner{"
    "projectV2(number:$number){viewerCanUpdate}}}"
)
PROJECT_ROLE = (
    "mutation($project:ID!,$user:ID!){updateProjectV2Collaborators(input:{projectId:$project,"
    "collaborators:[{userId:$user,role:WRITER}]}){clientMutationId}}"
)


class _Gh:
    """`activate_protection`'s `Gh` over `manual.Target.gh`: a failed call raises, and a REST
    read is served once until the next `-X` write."""

    def __init__(self, t: manual.Target, env: dict[str, str] | None = None) -> None:
        self.t, self.env, self.reads = t, env, dict[tuple[str, ...], str]()

    def __call__(self, cmd: list[str]) -> str:
        key, read = tuple(cmd), cmd[1] == "api" and cmd[2] != "graphql" and "-X" not in cmd
        if read and key in self.reads:
            return self.reads[key]
        if "-X" in cmd:
            self.reads.clear()
        done = self.t.gh(*cmd[1:], env=self.env)
        if done.returncode != 0 or done.stdout is None:
            shown = " ".join(arg for arg in cmd if not arg.startswith("query="))
            raise RuntimeError(f"`{shown}` failed (rc={done.returncode}): {done.stderr}")
        if read:
            self.reads[key] = done.stdout
        return done.stdout


@dataclass
class _Read:
    """What the agent's token reads: its permission on the repository, whether it can update
    the linked Project, and its user's node id."""

    permission: str | None
    can_update: bool
    viewer: str | None


def _no_agent() -> manual.Unreadable:
    return manual.Unreadable("no agent account")


@dataclass
class _Run:
    t: manual.Target  # the person's
    gh: _Gh
    pr: int | None
    repository: dict[str, Any] | manual.Unreadable
    login: str = ""
    token: str | manual.Unreadable = ""
    linked: tuple[str, int, str | None] | manual.Unreadable = field(default_factory=_no_agent)
    read: _Read | manual.Unreadable = field(default_factory=_no_agent)

    def agent_env(self) -> dict[str, str]:
        return {**person_env(), "GH_TOKEN": manual._ok(self.token)}

    def agent_gh(self) -> _Gh:
        return _Gh(self.t, self.agent_env())

    def reread(self) -> _Read:
        """One GraphQL read with the agent's token, the Project's role only while one is linked."""
        owner, name = self.t.repo.split("/")
        project = self.linked if isinstance(self.linked, tuple) else None
        number = ("-F", f"number={project[1]}") if project else ()
        query = (
            f"query($owner:String!,$name:String!,$number:Int!){{{AGENT_READ} {PROJECT_READ}}}"
            if project
            else f"query($owner:String!,$name:String!){{{AGENT_READ}}}"
        )
        owned = ("-f", f"owner={owner}", "-f", f"name={name}", *number, "-f", f"query={query}")
        read = manual._gh_read(self.t, "api", "graphql", *owned, env=self.agent_env())
        # A repository the token cannot see is `null` beside `errors`, exit 1 (observed).
        data = read.get("data") if isinstance(read, dict) else None
        if not isinstance(data, dict):
            raise manual.Unreadable(f"the agent's permission read as {read}")
        projected = (data.get("repositoryOwner") or {}).get("projectV2") or {}
        return _Read(
            (data.get("repository") or {}).get("viewerPermission"),
            projected.get("viewerCanUpdate") is True,
            (data.get("viewer") or {}).get("id"),
        )


class _Ambiguous(Exception):
    """No one agent account: a `conflict agent`."""


def steps(
    t: manual.Target, branch: str, choice: str | None, linked: list[dict[str, Any]]
) -> list[Step]:
    """The post-merge steps in order, over `linked`, the Projects linked to the repository;
    the agent's among them only with an agent account, and a run whose agent account is
    not one is a single `conflict agent`."""
    pt = replace(
        t, gh=lambda *args, env=None: t.gh(*args, env=env if env is not None else person_env())
    )
    try:
        login = _agent_login(pt, choice)
    except _Ambiguous as exc:
        return [Step("agent", "conflict", str(exc))]
    except manual.Unreadable as exc:
        return [Step("agent", "conflict", f"cannot read: {exc}")]
    try:
        pr = _merged(pt, branch)
    except manual.Unreadable as exc:
        raise InstallError(f"the merged installation PR: {exc}") from None
    run = _Run(pt, _Gh(pt), pr, manual._kept(lambda: _repository(pt)))
    classifiers: list[tuple[str, Callable[[_Run], Step]]] = [("protection", _protection)]
    if login is not None:
        run.login = login
        run.token = manual._kept(lambda: _token(pt, login))
        run.linked = manual._kept(lambda: _one_linked(pt, linked))
        run.read = manual._kept(run.reread)
        classifiers += [
            ("agent-collaborator", _collaborator),
            ("agent-project", _project),
            ("approval-ruleset", _approval),
            ("auto-merge", _auto_merge),
        ]
    return [_classified(label, run, classify) for label, classify in classifiers]


def _one_linked(t: manual.Target, linked: list[dict[str, Any]]) -> tuple[str, int, str | None]:
    """The owner, number and URL of the one Project linked to the repository."""
    if len(linked) != 1:
        raise manual.Unreadable(f"{len(linked)} Projects linked to {t.repo}")
    return t.repo.split("/")[0], int(linked[0]["number"]), linked[0].get("url")


def _repository(t: manual.Target) -> dict[str, Any]:
    """`repos/<owner>/<name>`, one read for `protection` and `auto-merge`; `gh api`
    prints GitHub's error object on a 4xx, which names neither field."""
    data = manual._gh_read(t, "api", f"repos/{t.repo}")
    if (
        isinstance(data, dict)
        and isinstance(data.get("default_branch"), str)
        and "allow_auto_merge" in data
    ):
        return data
    raise manual.Unreadable(f"`gh api repos/{t.repo}` printed an unexpected shape: {data}")


def _protected(t: manual.Target, repo: dict[str, Any]) -> bool:
    """The default branch's rules require both process checks."""
    branch = repo["default_branch"]
    rules = manual._gh_read(t, "api", f"repos/{t.repo}/rules/branches/{branch}")
    try:
        if not isinstance(rules, list):
            raise TypeError
        required = set(activate_protection.required_contexts(rules))
    except (KeyError, TypeError):
        raise manual.Unreadable(f"the rules of {branch} read as {rules}") from None
    return set(activate_protection.contexts()) <= required


def _agent_login(t: manual.Target, choice: str | None) -> str | None:
    """The one github.com account `gh auth status` lists besides the active one, or the one
    `choice` names among several."""
    read = manual._gh_read(t, "auth", "status", "--json", "hosts")
    try:
        accounts = read["hosts"].get("github.com", [])
        others = [str(account["login"]) for account in accounts if not account["active"]]
    except (AttributeError, KeyError, TypeError):
        raise manual.Unreadable(
            "`gh auth status --json hosts` printed an unexpected shape"
        ) from None
    if choice in others or (choice is None and len(others) < 2):
        return choice or next(iter(others), None)
    named = ", ".join(others) or "none"
    if choice:
        raise _Ambiguous(f"--agent {choice} is not among the other github.com accounts: {named}")
    raise _Ambiguous(f"github.com accounts besides the active one: {named}; choose with --agent")


def _merged(t: manual.Target, branch: str) -> int | None:
    fields = ("--head", branch, "--state", "merged", "--json", "number")
    read = manual._gh_read(t, "pr", "list", "--repo", t.repo, *fields)
    try:
        return next((int(pull["number"]) for pull in read), None)
    except (KeyError, TypeError, ValueError):
        raise manual.Unreadable(f"`gh pr list` printed an unexpected shape: {read}") from None


def _token(t: manual.Target, login: str) -> str:
    done = t.gh("auth", "token", "--user", login)
    if done.returncode != 0 or done.stdout is None or not done.stdout.strip():
        raise manual.Unreadable(
            f"`gh auth token --user {login}` (rc={done.returncode}): {done.stderr}"
        )
    return done.stdout.strip()


def _classified(label: str, run: _Run, classify: Callable[[_Run], Step]) -> Step:
    """`classify`'s step, a failed read or a refusal as its `conflict`, and before the merge
    every step not `unchanged` as `after-merge`."""
    try:
        step = classify(run)
    except activate_protection.Refusal as exc:
        step = Step(label, "conflict", str(exc))
    except (manual.Unreadable, RuntimeError) as exc:
        step = Step(label, "conflict", f"cannot read: {exc}")
    if run.pr is None and step.status != "unchanged":
        return Step(label, "after-merge", step.detail)
    if step.apply is not None:
        step.apply = _guarded(label, step.apply)
    return step


def _guarded(label: str, apply: Callable[[], bool]) -> Callable[[], bool]:
    def guarded() -> bool:
        try:
            return apply()
        except (manual.Unreadable, RuntimeError, activate_protection.Refusal) as exc:
            raise InstallError(f"{label}: {exc}") from None

    return guarded


def _checks() -> str:
    return " and ".join(activate_protection.contexts())


def _protection(run: _Run) -> Step:
    repository = manual._ok(run.repository)
    branch = repository["default_branch"]
    if _protected(run.t, repository):
        return Step("protection", "unchanged", f"the rules of {branch} require {_checks()}")
    if run.pr is None:
        detail = f"a ruleset requiring {_checks()} on {branch}, as observed on the merged PR"
        return Step("protection", "planned", detail)
    repo, branch, checks = activate_protection.preflight(run.gh, run.pr)
    want = activate_protection.desired(branch, checks)
    action, ruleset_id, _ = activate_protection.plan(run.gh, repo, want)
    if action == "unchanged":
        detail = f"ruleset {ruleset_id} is as planned, yet the rules of {branch} lack {_checks()}"
        return Step("protection", "conflict", detail)

    def apply() -> bool:
        written = activate_protection.write(run.gh, repo, ruleset_id, want)
        activate_protection.read_back(run.gh, repo, written, branch, checks)
        return True

    detail = f"{action} ruleset {want['name']!r} requiring {_checks()} on {branch}"
    return Step("protection", "planned", detail, apply)


def _collaborator(run: _Run) -> Step:
    read, repo, login = manual._ok(run.read), run.t.repo, run.login
    if read.permission in manual.AGENT_PERMISSIONS:
        return Step("agent-collaborator", "unchanged", f"{login} has {read.permission} on {repo}")

    def apply() -> bool:
        run.gh(
            [
                "gh",
                "api",
                "-X",
                "PUT",
                f"repos/{repo}/collaborators/{login}",
                "-f",
                "permission=push",
            ]
        )
        agent = run.agent_gh()
        for invitation in _json(agent, ["gh", "api", "user/repository_invitations"]):
            if (invitation.get("repository") or {}).get("full_name") == repo:
                agent(
                    ["gh", "api", "-X", "PATCH", f"user/repository_invitations/{invitation['id']}"]
                )
        permission = run.reread().permission
        if permission not in manual.AGENT_PERMISSIONS:
            raise InstallError(f"agent-collaborator: {login} reads {permission} on {repo}")
        return True

    detail = f"invite {login} to {repo} with push permission; {login} accepts"
    return Step("agent-collaborator", "planned", detail, apply)


def _project(run: _Run) -> Step:
    owner, number, url = manual._ok(run.linked)
    read, login, where = manual._ok(run.read), run.login, url or f"{owner}'s Project {number}"
    if read.can_update:
        return Step("agent-project", "unchanged", f"{login} can update {where}")

    def apply() -> bool:
        if read.viewer is None:
            raise InstallError(f"agent-project: the read of {login} names no user id")
        project = manual.areas(run.t, (owner, number, url)).project
        fields = ("-f", f"project={project}", "-f", f"user={read.viewer}")
        run.gh(["gh", "api", "graphql", *fields, "-f", f"query={PROJECT_ROLE}"])
        if not run.reread().can_update:
            raise InstallError(f"agent-project: {login} cannot update {where} after the role")
        return True

    return Step("agent-project", "planned", f"{login} gets the WRITER role on {where}", apply)


def _approval(run: _Run) -> Step:
    want = json.loads(APPROVAL.read_text(encoding="utf-8"))
    action, ruleset_id, _ = activate_protection.plan(run.gh, run.t.repo, want)
    if action == "unchanged":
        return Step("approval-ruleset", "unchanged", f"ruleset {ruleset_id} {want['name']!r}")

    def apply() -> bool:
        activate_protection.write(run.gh, run.t.repo, ruleset_id, want)
        again, _, lines = activate_protection.plan(run.gh, run.t.repo, want)
        if again != "unchanged":
            raise InstallError(f"approval-ruleset reads back as {'; '.join(lines)}")
        return True

    return Step("approval-ruleset", "planned", f"{action} ruleset {want['name']!r}", apply)


def _auto_merge(run: _Run) -> Step:
    repo = run.t.repo
    if manual._ok(run.repository)["allow_auto_merge"] is True:
        return Step("auto-merge", "unchanged", f"{repo} allows auto-merge")

    def apply() -> bool:
        run.gh(["gh", "repo", "edit", repo, "--enable-auto-merge"])
        if _repository(run.t)["allow_auto_merge"] is not True:
            raise InstallError(f"auto-merge: {repo} reads allow_auto_merge false")
        return True

    return Step("auto-merge", "planned", f"allow auto-merge on {repo}", apply)


if __name__ == "__main__":
    sys.exit("post_merge.py is imported by init.py; run `agent-process init`")
