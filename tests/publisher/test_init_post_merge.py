"""The agent identity and the post-merge steps of the installer (change
init-runs-post-merge-steps): `after-merge` before the installation PR is merged, written by
the confirmed run after it, against the `FakeGitHub` of `init_harness.py`."""

from __future__ import annotations

import json
from types import ModuleType
from typing import Callable

import pytest

from tests.publisher.init_harness import (
    AGENT,
    AGENT_TOKEN,
    HOST,
    LINE,
    ROOT,
    Runner,
    Sandbox,
    _installed,
    agent_account,
    agent_identity,
    check_run,
    install,
    load_init,
)
from tests.publisher.init_reads import (
    PROCESS_CHECKS,
    _gh_kind,
    _git_state,
    _manual_rows,
    _pushes,
    _row,
)


@pytest.mark.parametrize(
    ("arrange", "named"),
    [
        pytest.param(lambda sb: None, "git config agent-process.bot is not set", id="no-bot"),
        pytest.param(
            lambda sb: agent_identity(sb, token=None), "gh holds no token for agent", id="no-token"
        ),
        pytest.param(lambda sb: agent_identity(sb, token="person-token"), "ADMIN", id="admin"),
        pytest.param(lambda sb: agent_identity(sb, token="stranger-token"), "READ", id="read"),
    ],
)
def test_agent_identity_pending_is_manual(
    sandbox: Sandbox,
    capfd: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    arrange: Callable[[Sandbox], None],
    named: str,
) -> None:
    """Scenario: Identity pending."""
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("GIT_CONFIG_GLOBAL", raising=False)  # the sandbox's HOME holds it
    sandbox.github.allow_auto_merge = True
    sandbox.github.permissions.update({"person-token": "ADMIN", "stranger-token": "READ"})
    arrange(sandbox)
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    row = _row(_manual_rows(capfd.readouterr().out), "agent-identity")
    assert "(cannot read: " not in row, row
    assert named in row and init.manual.IDENTITY_FIX in row, row
    assert "-token" not in row, row


def test_agent_identity_holds(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Identity holds — read with the bot's token, not the session's."""
    monkeypatch.setenv("GH_TOKEN", "person-token")
    agent_identity(sandbox)
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    manual = _manual_rows(capfd.readouterr().out)
    assert not [ln for ln in manual if ln.startswith("manual agent-identity: ")], manual
    tokened = [args for token, args in sandbox.github.tokened if token == "agent-token"]
    assert tokened == [["repo", "view", "--json", "viewerPermission"]], tokened
    assert "agent-token" not in " ".join(manual)


# --- the post-merge steps (change init-runs-post-merge-steps) ----------------------------

POST_MERGE = [
    "protection",
    "agent-collaborator",
    "agent-project",
    "approval-ruleset",
    "auto-merge",
]
TEMPLATES = ROOT / "skills" / "agent-process" / "templates"
APPROVAL = json.loads((TEMPLATES / "approval_ruleset.json").read_text(encoding="utf-8"))
PROCESS_RULESET = json.loads((TEMPLATES / "ruleset.json").read_text(encoding="utf-8"))
# Words only a post-merge transition's `gh` call carries.
POST_MERGE_CALLS = (
    "rulesets",
    "check-runs",
    "collaborators/",
    "repository_invitations",
    "nameWithOwner",
    "updateProjectV2Collaborators",
    "viewerCanUpdate",
)


def _post_merge_call(args: list[str]) -> bool:
    text = " ".join(args)
    commands = (["pr", "view"], ["repo", "edit"])
    return args[0] == "auth" or args[:2] in commands or any(w in text for w in POST_MERGE_CALLS)


def _post_merge(out: str) -> list[tuple[str, str]]:
    """The post-merge lines as (status, label), in printed order."""
    return [(status, label) for status, label in LINE.findall(out) if label in POST_MERGE]


def _merged(init: ModuleType, sb: Sandbox) -> None:
    """The installation PR opened by a confirmed run, then merged."""
    _installed(init, sb)
    (pull,) = sb.github.pulls
    pull["state"] = "MERGED"


def _done_states(sb: Sandbox) -> None:
    """Every post-merge state as the post-merge run leaves it."""
    sb.github.required_checks = list(PROCESS_CHECKS)
    sb.github.permissions[AGENT_TOKEN] = "WRITE"
    sb.github.project_writers.add(AGENT)
    sb.github.rulesets[1000] = {**APPROVAL, "id": 1000, "source_type": "Repository"}
    sb.github.allow_auto_merge = True


def _non_reads(runner: Runner) -> list[str]:
    return sorted(kind for kind in map(_gh_kind, runner.gh()) if kind != "read")


def test_post_merge_waits_for_the_merge(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenarios: Before the merge; Dry-run (with an agent account). The PR body lists the
    `after-merge` lines; a rerun that meets the PR open with another list rewrites it."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    assert _post_merge(capfd.readouterr().out) == [("after-merge", "protection")]
    (pull,) = sandbox.github.pulls
    assert "after-merge protection:" in pull["body"], pull["body"]
    assert "after-merge agent-collaborator:" not in pull["body"], pull["body"]
    agent_account(sandbox)
    runner.log.clear()
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    assert _post_merge(capfd.readouterr().out) == [("after-merge", label) for label in POST_MERGE]
    assert _non_reads(runner) == []
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    assert _post_merge(out) == [("after-merge", label) for label in POST_MERGE], out
    assert _non_reads(runner) == ["pr-edit"]
    assert pull["body"].startswith(f"Closes #{sandbox.github.issues[0]['number']}"), pull["body"]
    for label in POST_MERGE:
        assert f"after-merge {label}:" in pull["body"], (label, pull["body"])
    assert AGENT in pull["body"] and AGENT_TOKEN not in out + pull["body"]
    runner.log.clear()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    assert _non_reads(runner) == []


def test_post_merge_upgrade_done_is_unchanged(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Upgrade with the steps done — the PR is open and every state is done."""
    init = load_init()
    agent_account(sandbox)
    _installed(init, sandbox)
    _done_states(sandbox)
    capfd.readouterr()
    assert install(init, sandbox, "--dry-run") == 0
    out = capfd.readouterr().out
    assert _post_merge(out) == [("unchanged", label) for label in POST_MERGE], out
    assert "after-merge" not in out


def test_post_merge_steps_are_written(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenarios: After the merge; Post-merge run; A clone with the agent's identity."""
    init = load_init()
    agent_account(sandbox)
    _merged(init, sandbox)
    monkeypatch.setenv("GH_TOKEN", "person-session-token")
    monkeypatch.setenv("GITHUB_TOKEN", "person-session-token")
    runner = Runner(init, HOST, sandbox.github)
    calls = len(sandbox.github.calls)
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    printed = capfd.readouterr()
    out = printed.out
    statuses = _post_merge(out)
    assert [label for status, label in statuses if status == "written"] == POST_MERGE, out
    assert AGENT_TOKEN not in printed.out + printed.err
    assert _non_reads(runner) == sorted(
        ["ruleset", "ruleset", "collaborator", "accept", "project-role", "auto-merge"]
    )
    assert not _pushes(runner)
    github = sandbox.github
    names = {ruleset["name"] for ruleset in github.rulesets.values()}
    assert names == {APPROVAL["name"], PROCESS_RULESET["name"]}, github.rulesets
    assert github.allow_auto_merge and github.permissions[AGENT_TOKEN] == "WRITE"
    assert AGENT in github.project_writers
    as_agent = []
    for args, env in github.calls[calls:]:
        if _post_merge_call(args):
            assert env is not None, args
        if env is not None:
            assert "GITHUB_TOKEN" not in env, (args, env)
            assert env.get("GH_TOKEN") in (None, AGENT_TOKEN), (args, env)
        if env is not None and env.get("GH_TOKEN") == AGENT_TOKEN:
            as_agent.append(args)
    for args in as_agent:
        accept = _gh_kind(args) == "accept" or args[-1] == "user/repository_invitations"
        assert accept or "viewerPermission" in args[-1], args
    assert any(_gh_kind(args) == "accept" for args in as_agent), as_agent
    runner.log.clear()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    # A confirmed run prints each step when classified and again when performed.
    assert _post_merge(out) == [("unchanged", label) for label in POST_MERGE] * 2, out
    assert _non_reads(runner) == []


def test_post_merge_protection_not_observed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Quality not observed — no successful `agent-review / agent-review` run."""
    init = load_init()
    agent_account(sandbox)
    _merged(init, sandbox)
    sandbox.github.check_runs = [check_run("agent-process / quality")]
    runner = Runner(init, HOST, sandbox.github)
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 2
    out = capfd.readouterr().out
    (line,) = [ln for ln in out.splitlines() if ln.startswith("conflict protection: ")]
    assert "agent-review / agent-review" in line, line
    assert _non_reads(runner) == []
    assert sandbox.github.rulesets == {} and not sandbox.github.allow_auto_merge


@pytest.mark.parametrize("others", [[], ["second-bot"]], ids=["one", "chosen"])
def test_agent_account(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], others: list[str]
) -> None:
    """Scenario: Agent account — the one non-active account, or the one `--agent` chooses."""
    agent_account(sandbox)
    for login in others:
        agent_account(sandbox, login, f"gho_{login}")
    init = load_init()
    chosen = ["--agent", AGENT] if others else []
    assert install(init, sandbox, "--dry-run", *chosen) == 0
    out = capfd.readouterr().out
    (line,) = [ln for ln in out.splitlines() if ln.startswith("after-merge agent-collaborator: ")]
    assert AGENT in line and not [login for login in others if login in line], line


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
@pytest.mark.parametrize("chosen", [[], ["--agent", "stranger"]], ids=["none", "unknown"])
def test_agent_account_ambiguous(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str, chosen: list[str]
) -> None:
    """Scenario: Several accounts — `conflict agent` names both, before any write."""
    agent_account(sandbox)
    agent_account(sandbox, "second-bot", "gho_second")
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    assert install(init, sandbox, mode, *chosen, runner=runner) == 2
    out = capfd.readouterr().out
    (line,) = [ln for ln in out.splitlines() if ln.startswith("conflict agent: ")]
    assert AGENT in line and "second-bot" in line, line
    assert _non_reads(runner) == []
    assert (sandbox.github.state(), _git_state(sandbox)) == before
