"""`agent_identity.py` (change agent-identity, design D1–D4).

One test per scenario of the `distribution` delta; the scenario name is the test name.
The person's `gh`, the bot's `gh` and `git` are fakes over one shared state that answer by
command shape and record every call; the clone's settings file is a real file.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.publisher.delivery_fakes import PROJECT, ROOT, load_script

REPO = "owner/repo"
BOT = "agent-bot"
TOKEN = "bot-token"
HELPER = "credential.https://github.com.helper"
NAME = "agent-process person approves"
SETTINGS = ".claude/settings.local.json"
TEMPLATE = ROOT / "skills" / "agent-process" / "templates" / "approval_ruleset.json"
GIT_WRITES = ("--replace-all", "--add", "--unset-all", "--unset")


class World:
    """GitHub's and the clone's state that both identities see."""

    def __init__(self, *, role: str = "read", login: str = BOT) -> None:
        self.role = role  # the bot's `role_name` on the repository
        self.login = login  # the login the bot's token belongs to
        self.invitation: int | None = None
        self.writer = False  # the bot's write role on the linked Project
        self.helpers: list[str] = []  # this clone's credential helpers for github.com
        self.ignored = True  # `git check-ignore` of the settings file


class PersonGh:
    """The person's `gh`: the repository, the Project, the collaborator and the rulesets."""

    def __init__(self, world: World, *, token: bool = True) -> None:
        self.world = world
        self.token = token
        self.calls: list[list[str]] = []
        self.rulesets: dict[int, dict[str, Any]] = {}
        self.read_back: Any = None  # mutates the ruleset the next GET returns after a write

    def _ruleset(self, cmd: list[str]) -> str:
        self.calls.append(cmd)
        endpoint = next(arg for arg in cmd[2:] if not arg.startswith("-") and "/" in arg)
        if "--input" not in cmd:
            if endpoint == f"repos/{REPO}/rulesets":
                listed = [
                    {k: r[k] for k in ("id", "name", "source_type")} for r in self.rulesets.values()
                ]
                return json.dumps([listed])  # `--paginate --slurp`: one page
            return json.dumps(self.rulesets[int(endpoint.rsplit("/", 1)[1])])
        body = json.loads(Path(cmd[cmd.index("--input") + 1]).read_text(encoding="utf-8"))
        ruleset_id = 99 if endpoint.endswith("/rulesets") else int(endpoint.rsplit("/", 1)[1])
        served = copy.deepcopy(body) | {"id": ruleset_id, "source_type": "Repository"}
        self.rulesets[ruleset_id] = served if self.read_back is None else self.read_back(served)
        return json.dumps(served)

    def __call__(self, cmd: list[str]) -> str:
        if any(arg.startswith(f"repos/{REPO}/rulesets") for arg in cmd):
            return self._ruleset(cmd)
        if cmd[:4] == ["gh", "auth", "token", "--user"]:
            self.calls.append(cmd)
            assert cmd[4] == BOT
            if not self.token:
                raise RuntimeError(f"`{' '.join(cmd)}` failed (rc=1): no oauth token found")
            return TOKEN + "\n"
        if cmd[:3] == ["gh", "repo", "view"]:
            self.calls.append(cmd)
            owner, name = REPO.split("/")
            return json.dumps(
                {"owner": {"login": owner}, "name": name, "projectsV2": {"Nodes": [PROJECT]}}
            )
        if cmd == ["gh", "api", f"repos/{REPO}/collaborators/{BOT}/permission"]:
            self.calls.append(cmd)
            role = self.world.role
            permission = {"maintain": "write", "triage": "read"}.get(role, role)
            return json.dumps({"permission": permission, "role_name": role})
        if cmd[:5] == ["gh", "api", "-X", "PUT", f"repos/{REPO}/collaborators/{BOT}"]:
            self.calls.append(cmd)
            assert "permission=push" in cmd
            self.world.invitation = 7
            return json.dumps({"id": 7, "repository": {"full_name": REPO}})
        if cmd[:3] == ["gh", "api", "graphql"] and "updateProjectV2Collaborators" in str(cmd):
            self.calls.append(cmd)
            assert "projectId=PVT_1" in cmd and "userId=U_bot" in cmd
            self.world.writer = True
            return json.dumps(
                {"data": {"updateProjectV2Collaborators": {"clientMutationId": None}}}
            )
        raise AssertionError(f"unexpected person gh call: {cmd}")

    def writes(self) -> list[list[str]]:
        return [c for c in self.calls if "-X" in c or "mutation" in str(c)]


class BotGh:
    """The bot's `gh`, built from the token the script read."""

    def __init__(self, world: World, token: str) -> None:
        assert token == TOKEN
        self.world = world
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str]) -> str:
        self.calls.append(cmd)
        if cmd == ["gh", "api", "user"]:
            return json.dumps({"login": self.world.login, "node_id": "U_bot"})
        if cmd == ["gh", "api", "user/repository_invitations"]:
            pending = self.world.invitation
            return json.dumps(
                [] if pending is None else [{"id": pending, "repository": {"full_name": REPO}}]
            )
        if cmd == ["gh", "api", "-X", "PATCH", "user/repository_invitations/7"]:
            assert self.world.invitation == 7
            self.world.invitation, self.world.role = None, "write"
            return ""
        if cmd[:3] == ["gh", "api", "graphql"] and "viewerCanUpdate" in str(cmd):
            assert "id=PVT_1" in cmd
            return json.dumps({"data": {"node": {"viewerCanUpdate": self.world.writer}}})
        raise AssertionError(f"unexpected bot gh call: {cmd}")

    def writes(self) -> list[list[str]]:
        return [c for c in self.calls if "-X" in c]


class FakeGit:
    """`git` over this clone's config and ignore rules."""

    def __init__(self, world: World) -> None:
        self.world = world
        self.calls: list[list[str]] = []

    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(cmd)
        args = cmd[cmd.index("-C") + 2 :] if "-C" in cmd else cmd[1:]

        def done(code: int, out: str = "") -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(cmd, code, out, "")

        if args[:2] == ["check-ignore", "-q"]:
            assert args[2] == SETTINGS
            return done(0 if self.world.ignored else 1)
        if args == ["config", "--local", "--get-all", HELPER]:
            helpers = self.world.helpers
            return done(0, "".join(f"{h}\n" for h in helpers)) if helpers else done(1)
        if args[:3] == ["config", "--local", "--replace-all"] and args[3] == HELPER:
            self.world.helpers = [args[4]]
            return done(0)
        if args[:3] == ["config", "--local", "--add"] and args[3] == HELPER:
            self.world.helpers.append(args[4])
            return done(0)
        raise AssertionError(f"unexpected git call: {cmd}")

    def writes(self) -> list[list[str]]:
        return [c for c in self.calls if any(flag in c for flag in GIT_WRITES)]


def _clone(tmp_path: Path, settings: dict[str, Any] | None) -> Path:
    if settings is not None:
        (tmp_path / ".claude").mkdir()
        text = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"
        (tmp_path / SETTINGS).write_text(text, encoding="utf-8")
    return tmp_path


class Run:
    """One invocation of the script over `world`, with the fakes it used."""

    def __init__(self, world: World, root: Path, *, token: bool = True) -> None:
        self.gh = PersonGh(world, token=token)
        self.git = FakeGit(world)
        self.bots: list[BotGh] = []
        self.world, self.root = world, root

    def bot(self, token: str) -> BotGh:
        made = BotGh(self.world, token)
        self.bots.append(made)
        return made

    def __call__(self, mode: str, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
        module = load_script("agent_identity")
        with pytest.raises(SystemExit) as exc:
            module.main(
                ["--bot", BOT, mode], gh=self.gh, bot=self.bot, git=self.git, root=self.root
            )
        captured = capsys.readouterr()
        return int(exc.value.code or 0), captured.out + captured.err

    def writes(self) -> list[list[str]]:
        bot_writes = [c for bot in self.bots for c in bot.writes()]
        return self.gh.writes() + bot_writes + self.git.writes()

    def transitions(self, out: str) -> list[str]:
        return [line for line in out.splitlines() if line.startswith(("planned", "unchanged"))]


KEPT = {"permissions": {"allow": ["Bash(ls)"]}, "env": {"OTHER": "1"}}


def _settings(root: Path) -> dict[str, Any]:
    return json.loads((root / SETTINGS).read_text(encoding="utf-8"))


def test_approval_ruleset_body() -> None:
    """Scenario: Merge from Claude Code — the rule that refuses an unapproved merge."""
    body = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert body["name"] == NAME
    assert (body["target"], body["enforcement"], body["bypass_actors"]) == (
        "branch",
        "active",
        [],
    )
    assert body["conditions"] == {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}
    (rule,) = body["rules"]
    assert rule["type"] == "pull_request"
    assert rule["parameters"] == {
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": False,
        "require_last_push_approval": False,
        "required_approving_review_count": 1,
        "required_review_thread_resolution": False,
    }


def test_confirmed_run_on_a_fresh_repository(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    world = World()
    root = _clone(tmp_path, KEPT)
    run = Run(world, root)
    code, out = run("--confirm", capsys)
    assert code == 0, out
    assert [line.split(":")[0] for line in run.transitions(out)][:5] == [
        "planned collaborator",
        "planned project",
        "planned settings",
        "planned git",
        "planned ruleset",
    ]
    assert (world.role, world.invitation, world.writer) == ("write", None, True)
    assert _settings(root) == {**KEPT, "env": {"OTHER": "1", "GH_TOKEN": TOKEN}}
    assert world.helpers == ["", "!gh auth git-credential"]
    (body,) = [b for b in run.gh.rulesets.values() if b["name"] == NAME]
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert {key: body[key] for key in template} == template
    assert "restart" in out
    assert TOKEN not in out


@pytest.mark.parametrize(
    ("case", "named"),
    [
        ("not-ignored", f"{SETTINGS} is not git-ignored"),
        ("no-token", f"no gh token of {BOT}"),
        ("other-login", "belongs to someone-else"),
        ("admin", f"{BOT} is an admin"),
    ],
    ids=["not-ignored", "no-token", "other-login", "admin"],
)
def test_a_precondition_fails(
    tmp_path: Path, case: str, named: str, capsys: pytest.CaptureFixture[str]
) -> None:
    world = World(
        role="admin" if case == "admin" else "read",
        login="someone-else" if case == "other-login" else BOT,
    )
    world.ignored = case != "not-ignored"
    root = _clone(tmp_path, KEPT)
    run = Run(world, root, token=case != "no-token")
    code, out = run("--confirm", capsys)
    assert code == 2, out
    assert named in out
    assert run.writes() == []
    assert _settings(root) == KEPT


def test_rerun(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    world = World()
    root = _clone(tmp_path, None)
    first = Run(world, root)
    assert first("--confirm", capsys)[0] == 0
    again = Run(world, root)
    again.gh.rulesets = first.gh.rulesets
    code, out = again("--confirm", capsys)
    assert code == 0, out
    lines = again.transitions(out)
    assert len(lines) == 5 and all(line.startswith("unchanged") for line in lines), out
    assert again.writes() == []


def test_dry_run_issues_only_reads(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    world = World()
    root = _clone(tmp_path, KEPT)
    run = Run(world, root)
    code, out = run("--dry-run", capsys)
    assert code == 0, out
    lines = run.transitions(out)
    assert len(lines) == 5 and all(line.startswith("planned") for line in lines), out
    assert run.writes() == []
    assert _settings(root) == KEPT


def test_replan_names_the_differing_transition(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    world = World()
    run = Run(world, _clone(tmp_path, KEPT))

    def unapproved(served: dict[str, Any]) -> dict[str, Any]:
        served["rules"][0]["parameters"]["required_approving_review_count"] = 0
        return served

    run.gh.read_back = unapproved
    code, out = run("--confirm", capsys)
    assert code == 1, out
    assert "re-plan: ruleset is still planned" in out
