"""The installer's footprint, its remote writes and the Project phase.

`test_installed_footprint_is_closed` runs the real pinned OpenSpec.

`gh` never reaches GitHub: the runner hands it to `FakeGitHub` (change
v2-2g-c-project-provisioning, design D6), which answers the two reads in their observed
shapes and applies `project copy` and `project link` to its own Projects.

The module is imported inside the tests so that a missing symbol fails its own test
body. The fixture repository and the runner are described in `test_init.py`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from tests.publisher.init_harness import (
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
    git,
    install,
    load_init,
    snapshot,
    transitions,
)

# --- footprint and remote writes --------------------------------------------------------


def _consumer_repo(sb: Sandbox) -> None:
    (sb.root / "README.md").write_text("consumer\n", encoding="utf-8")
    git("init", "-q", cwd=sb.root)
    git("add", "-A", cwd=sb.root)
    git("commit", "-q", "-m", "initial", cwd=sb.root)


def test_installed_footprint_is_closed(sandbox: Sandbox) -> None:
    init = load_init()
    _consumer_repo(sandbox)
    runner = Runner(init, HOST, sandbox.github, real_npx=True)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    status = git("status", "--porcelain", "--untracked-files=all", cwd=sandbox.root)
    changed = {line[3:] for line in status.splitlines()}
    assert changed == set(init.OPENSPEC_OUTPUT) | CONSUMER_FILES
    settings = json.loads((sandbox.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {
        "extraKnownMarketplaces": {
            MARKETPLACE: {
                "source": {
                    "source": "github",
                    "repo": "ekolvah/agent-process-distribution",
                    "ref": f"v{CURRENT}",
                }
            }
        },
        "enabledPlugins": {PLUGIN: True},
        "hooks": {"SessionStart": [CHECK_GROUP]},
    }


def _gh_kind(args: list[str]) -> str:
    """`read`, `copy`, or `link`; any other `gh` command fails the test."""
    if args[:2] == ["repo", "view"]:
        return "read"
    if args[:2] == ["api", "graphql"] and not any("mutation" in part for part in args):
        return "read"
    if args[:2] == ["project", "copy"]:
        return "copy"
    if args[:2] == ["project", "link"]:
        return "link"
    raise AssertionError(f"gh command that is not a read, the copy, or the link: {args}")


def test_only_project_writes_remote(sandbox: Sandbox) -> None:
    init = load_init()
    _consumer_repo(sandbox)
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    kinds = [_gh_kind(args) for args in runner.gh()]
    assert (kinds.count("copy"), kinds.count("link")) == (1, 1), kinds
    for cmd in runner.log:
        assert not any("api.github.com" in part for part in cmd), cmd
        if Path(cmd[0]).name.lower().startswith("git"):
            assert not {"commit", "push"} & set(cmd), cmd
    assert git("rev-list", "--count", "HEAD", cwd=sandbox.root) == "1"
    assert git("status", "--porcelain", cwd=sandbox.root)


def test_dry_run_writes_nothing_remote(sandbox: Sandbox) -> None:
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state()
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    assert runner.gh("repo", "view") and runner.gh("api", "graphql")
    assert {_gh_kind(args) for args in runner.gh()} == {"read"}
    assert sandbox.github.state() == before


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
    for args in runner.gh():
        _gh_kind(args)
