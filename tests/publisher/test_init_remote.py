"""The installer's footprint, its remote writes, the installation PR and the Project phase.

`test_installed_footprint_is_closed` runs the real pinned OpenSpec.

`gh` never reaches GitHub: the runner hands it to `FakeGitHub` (change
v2-2g-c-project-provisioning, design D6), which answers the reads in their observed
shapes and applies `project copy`, `project link`, `issue create` and `pr create` to its own
state (change install-links-an-issue, design D4). The consumer is a clone of a local bare
`origin`, so the branch, commit and push are real git.

The module is imported inside the tests so that a missing symbol fails its own test
body. The fixture repository and the runner are described in `test_init.py`.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import pytest

from tests.publisher.init_harness import (
    BRANCH,
    CHECK_GROUP,
    CONSUMER_FILES,
    CURRENT,
    HOST,
    LABELS,
    MARKETPLACE,
    OWNER,
    PLUGIN,
    REPO_NAME,
    TITLE,
    FakeGitHub,
    Runner,
    Sandbox,
    _installed,
    git,
    install,
    load_init,
    snapshot,
    transitions,
)

# --- footprint and remote writes --------------------------------------------------------

ISSUE_TITLE = f"Install agent-process {CURRENT}"
ONBOARDING = [label for label in LABELS if label.startswith("onboarding-")]


def _refs(path: Path) -> str:
    return git("for-each-ref", "--format=%(refname) %(objectname)", cwd=path)


def _git_state(sb: Sandbox) -> tuple[str, str, str]:
    """The consumer's refs and HEAD, and `origin`'s refs."""
    return _refs(sb.root), git("rev-parse", "HEAD", cwd=sb.root), _refs(sb.origin)


def test_installed_footprint_is_closed(sandbox: Sandbox) -> None:
    """Scenario: Fresh repository — the installation commit carries exactly the installer's
    files, and nothing is left uncommitted."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github, real_npx=True)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    assert git("status", "--porcelain", "--untracked-files=all", cwd=sandbox.root) == ""
    changed = git("diff", "--name-only", "main..HEAD", cwd=sandbox.root)
    assert set(changed.splitlines()) == set(init.OPENSPEC_OUTPUT) | CONSUMER_FILES
    settings = json.loads((sandbox.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {
        "extraKnownMarketplaces": {
            MARKETPLACE: {
                "source": {
                    "source": "github",
                    "repo": "ekolvah/agent-process-distribution",
                    "ref": "stable",
                },
                "autoUpdate": True,
            }
        },
        "hooks": {"SessionStart": [CHECK_GROUP]},
    }


def _gh_kind(args: list[str]) -> str:
    """`read`, `copy`, `link`, `issue` or `pr`; any other `gh` command fails the test."""
    if args[:2] in (["repo", "view"], ["issue", "list"], ["pr", "list"]):
        return "read"
    if args[:2] == ["api", "graphql"] and not any("mutation" in part for part in args):
        return "read"
    kinds = {
        ("project", "copy"): "copy",
        ("project", "link"): "link",
        ("issue", "create"): "issue",
        ("pr", "create"): "pr",
    }
    if tuple(args[:2]) in kinds:
        return kinds[args[0], args[1]]
    raise AssertionError(f"gh command that is not a read or an allowed write: {args}")


def _pushes(runner: Runner) -> list[list[str]]:
    return [cmd for cmd in runner.log if Path(cmd[0]).stem.lower() == "git" and "push" in cmd]


def test_remote_writes_are_project_and_pr(sandbox: Sandbox) -> None:
    """Scenario: Confirmed run."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    main = git("rev-parse", "main", cwd=sandbox.root)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    kinds = sorted(_gh_kind(args) for args in runner.gh())
    assert [kind for kind in kinds if kind != "read"] == ["copy", "issue", "link", "pr"], kinds
    (push,) = _pushes(runner)
    assert push[-1] == BRANCH, push
    for cmd in runner.log:
        assert not any("api.github.com" in part for part in cmd), cmd
    assert git("rev-parse", "main", cwd=sandbox.root) == main
    assert git("rev-parse", "main", cwd=sandbox.origin) == main
    assert git("rev-list", "--count", "main", cwd=sandbox.root) == "1"


def test_dry_run_writes_nothing_remote(sandbox: Sandbox) -> None:
    """Scenario: Dry-run."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    assert runner.gh("repo", "view") and runner.gh("api", "graphql")
    assert {_gh_kind(args) for args in runner.gh()} == {"read"}
    assert (sandbox.github.state(), _git_state(sandbox)) == before


# --- the installation PR ----------------------------------------------------------------


def test_install_opens_the_pr(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Fresh install opens the PR."""
    init = load_init()
    assert install(init, sandbox, "--confirm") == 0
    out = capfd.readouterr().out
    (issue,) = sandbox.github.issues
    assert (issue["title"], issue["state"]) == (ISSUE_TITLE, "OPEN")
    (pull,) = sandbox.github.pulls
    assert (pull["head"], pull["base"], pull["state"]) == (BRANCH, "main", "OPEN")
    assert pull["body"].startswith(f"Closes #{issue['number']}"), pull["body"]
    (line,) = [ln for ln in out.splitlines() if ln.startswith("written onboarding-pr:")]
    assert pull["url"] in line, line
    assert git("rev-list", "--count", f"main..{BRANCH}", cwd=sandbox.origin) == "1"
    changed = git("diff", "--name-only", f"main..{BRANCH}", cwd=sandbox.origin)
    assert set(changed.splitlines()) == set(init.OPENSPEC_OUTPUT) | CONSUMER_FILES
    assert git("branch", "--show-current", cwd=sandbox.root) == BRANCH


def test_open_issue_is_reused(sandbox: Sandbox) -> None:
    """Scenario: Open issue is reused — matched on the exact title."""
    init = load_init()
    sandbox.github.issue(f"{ISSUE_TITLE} (draft)")
    issue = sandbox.github.issue(ISSUE_TITLE)
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    assert not runner.gh("issue", "create")
    (pull,) = sandbox.github.pulls
    assert pull["body"].startswith(f"Closes #{issue['number']}"), pull["body"]


def test_nothing_to_install(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Nothing to install — the installation merged into the default branch."""
    init = load_init()
    _installed(init, sandbox)
    git("switch", "-q", "main", cwd=sandbox.root)
    git("merge", "-q", "--ff-only", BRANCH, cwd=sandbox.root)
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    assert not [label for label in transitions(out) if label.startswith("onboarding-")], out
    assert {_gh_kind(args) for args in runner.gh()} == {"read"}
    assert (sandbox.github.state(), _git_state(sandbox)) == before


def test_rerun_after_merge(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Rerun after the merge — still on the installation branch."""
    init = load_init()
    _installed(init, sandbox)
    (pull,) = sandbox.github.pulls
    pull["state"] = "MERGED"
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    seen = transitions(out)
    assert {label: seen.get(label) for label in ONBOARDING} == dict.fromkeys(
        ONBOARDING, "unchanged"
    ), out
    for label in ONBOARDING:
        lines = [ln for ln in out.splitlines() if ln.startswith(f"unchanged {label}:")]
        assert lines and all(pull["url"] in ln for ln in lines), (label, out)
    assert {_gh_kind(args) for args in runner.gh()} == {"read"}
    assert not _pushes(runner)
    assert (sandbox.github.state(), _git_state(sandbox)) == before


def _dirty(init: ModuleType, sb: Sandbox) -> None:
    (sb.root / "notes.txt").write_text("mine\n", encoding="utf-8")


def _other_branch(init: ModuleType, sb: Sandbox) -> None:
    git("switch", "-q", "-c", "feature", cwd=sb.root)


def _branch_on_origin(init: ModuleType, sb: Sandbox) -> None:
    git("push", "-q", "origin", f"main:refs/heads/{BRANCH}", cwd=sb.root)


def _pr_closed(init: ModuleType, sb: Sandbox) -> None:
    _installed(init, sb)
    sb.github.pulls[0]["state"] = "CLOSED"


# Each row: arrange the starting point, and what the conflict line names.
UNSAFE: dict[str, tuple[Callable[[ModuleType, Sandbox], None], str]] = {
    "dirty": (_dirty, "git stash"),
    "other-branch": (_other_branch, "git switch main"),
    "branch-not-checked-out": (_branch_on_origin, f"git switch {BRANCH}"),
    "pr-closed": (_pr_closed, "closed"),
}


@pytest.mark.parametrize("case", list(UNSAFE))
def test_unsafe_starting_point(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str
) -> None:
    """Scenario: Unsafe starting point."""
    init = load_init()
    arrange, cause = UNSAFE[case]
    arrange(init, sandbox)
    before = (
        snapshot(sandbox.root, sandbox.home),
        sandbox.github.state(),
        _git_state(sandbox),
    )
    capfd.readouterr()
    assert install(init, sandbox, "--confirm") == 2
    out = capfd.readouterr().out
    (line,) = [ln for ln in out.splitlines() if ln.startswith("conflict onboarding-branch:")]
    assert cause in line, line
    assert "written" not in transitions(out).values()
    after = (snapshot(sandbox.root, sandbox.home), sandbox.github.state(), _git_state(sandbox))
    assert after == before


# --- the Project phase ------------------------------------------------------------------

CONSUMER = f"{OWNER}/{REPO_NAME}"
# Each row: arrange the fake, then (project-copy, project-link) of the plan, or the exit code
# alone when the read itself refuses (design D2 and the truncated list of D1).
PROJECT_STATES: dict[str, tuple[Callable[[FakeGitHub], Any], tuple[str, str] | int]] = {
    "linked-one": (lambda gh: gh.add("anything", linked=CONSUMER), ("unchanged", "unchanged")),
    "linked-several": (
        lambda gh: (gh.add(linked=CONSUMER), gh.add("other", linked=CONSUMER)),
        ("conflict", "conflict"),
    ),
    "none": (lambda gh: gh.add("another title"), ("planned", "planned")),
    "one-reusable": (
        lambda gh: (gh.add(), gh.add(closed=True)),
        ("unchanged", "planned"),
    ),
    "several-reusable": (lambda gh: (gh.add(), gh.add()), ("conflict", "conflict")),
    "only-closed": (lambda gh: gh.add(closed=True), ("conflict", "conflict")),
    "only-linked-elsewhere": (
        lambda gh: gh.add(linked=f"{OWNER}/elsewhere"),
        ("conflict", "conflict"),
    ),
    "truncated-list": (lambda gh: setattr(gh, "hidden", 1), 1),
}


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
@pytest.mark.parametrize("case", list(PROJECT_STATES))
def test_project_states(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str, mode: str
) -> None:
    init = load_init()
    arrange, expected = PROJECT_STATES[case]
    arrange(sandbox.github)
    runner = Runner(init, HOST, sandbox.github)
    before = (snapshot(sandbox.root, sandbox.home), sandbox.github.state())
    code = install(init, sandbox, mode, runner=runner)
    out = capfd.readouterr().out
    seen = transitions(out)
    if isinstance(expected, int):
        assert code == expected, out
        assert "project-copy" not in seen
        assert (snapshot(sandbox.root, sandbox.home), sandbox.github.state()) == before
        return
    plan = dict(zip(("project-copy", "project-link"), expected))
    for label, status in plan.items():
        assert f"{status} {label}:" in out, out
    if "conflict" in expected:
        assert code == 2, out
        assert "written" not in seen.values()
        assert (snapshot(sandbox.root, sandbox.home), sandbox.github.state()) == before
        return
    assert code == 0, out
    if case == "linked-one":
        assert not runner.gh("api", "graphql")
    if mode == "--confirm":
        assert seen == dict.fromkeys(LABELS, "written") | {
            label: "written" if status == "planned" else status for label, status in plan.items()
        }, out
        linked = [p for p in sandbox.github.projects if CONSUMER in p.repositories]
        assert len(linked) == 1


@pytest.mark.parametrize("fault", ["fail-before", "fail-after"])
@pytest.mark.parametrize("command", ["copy", "link"])
def test_project_command_faults(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], command: str, fault: str
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    sandbox.github.faults[command] = fault
    assert install(init, sandbox, "--confirm", runner=runner) == 1
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    copies, links = len(runner.gh("project", "copy")), len(runner.gh("project", "link"))
    expected = {
        ("copy", "fail-before"): (2, 1),
        ("copy", "fail-after"): (1, 1),
        ("link", "fail-before"): (1, 2),
        ("link", "fail-after"): (1, 1),
    }[command, fault]
    assert (copies, links) == expected
    if (command, fault) == ("link", "fail-after"):
        assert transitions(out)["project-copy"] == "unchanged"
        assert transitions(out)["project-link"] == "unchanged"
    titled = [p for p in sandbox.github.projects if p.title == TITLE]
    assert len(titled) == 1 and titled[0].repositories == {CONSUMER}


WORKFLOWS = [
    "Auto-add to project",
    "Item added",
    "Item reopened",
    "Item closed",
    "Pull request merged",
]


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_manual_actions_are_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, mode, runner=runner) == 0
    lines = capfd.readouterr().out.splitlines()
    visibility = [ln for ln in lines if ln.startswith("manual project-visibility: ")]
    workflows = [ln for ln in lines if ln.startswith("manual project-workflows: ")]
    assert len(visibility) == 1 and "visibility" in visibility[0]
    assert len(workflows) == 1 and all(name in workflows[0] for name in WORKFLOWS)
    areas = [ln for ln in lines if ln.startswith("manual project-areas: ")]
    assert len(areas) == 1 and "Area" in areas[0]
    channel = [ln for ln in lines if ln.startswith("manual plugin-channel: ")]
    assert len(channel) == 1, channel
    assert 'claude plugin marketplace add "ekolvah/agent-process-distribution#stable"' in channel[0]
    assert "Enable auto-update" in channel[0]
    assert f"claude plugin install {PLUGIN}" in channel[0]
    assert not [cmd for cmd in runner.log if Path(cmd[0]).stem.lower() == "claude"]
    for args in runner.gh():
        _gh_kind(args)


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_review_prerequisites_are_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, mode, runner=runner) == 0
    lines = capfd.readouterr().out.splitlines()
    rows = [ln for ln in lines if ln.startswith("manual review-")]
    assert len(rows) == 1 and rows[0].startswith("manual review-secret: "), rows
    assert "CLAUDE_CODE_OAUTH_TOKEN" in rows[0]
    assert f"https://github.com/{CONSUMER}/settings/secrets/actions" in rows[0]
    # `_gh_kind` fails on any `gh` command but the reads, the copy and the link: no secret.
    for args in runner.gh():
        _gh_kind(args)
