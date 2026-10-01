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
import subprocess
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
    TEMPLATE_WORKFLOWS,
    TITLE,
    FakeGitHub,
    Runner,
    Sandbox,
    _installed,
    empty_origin,
    empty_repository,
    git,
    install,
    load_init,
    snapshot,
    transitions,
    which,
)

# --- footprint and remote writes --------------------------------------------------------

ISSUE_TITLE = f"Install agent-process {CURRENT}"
ONBOARDING = [label for label in LABELS if label.startswith("onboarding-")]


def _refs(path: Path) -> str:
    return git("for-each-ref", "--format=%(refname) %(objectname)", cwd=path)


def _git_state(sb: Sandbox) -> tuple[str, str, str]:
    """The consumer's refs and HEAD, and `origin`'s refs. HEAD is read as written, so that an
    unborn one is a state too."""
    head = (sb.root / ".git" / "HEAD").read_text(encoding="utf-8")
    return _refs(sb.root), head, _refs(sb.origin)


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
    if args[:2] in (["repo", "view"], ["issue", "list"], ["pr", "list"], ["secret", "list"]):
        return "read"
    if args == ["api", f"repos/{OWNER}/{REPO_NAME}"]:
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


def test_repository_with_no_commits(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Repository with no commits — the base is the branch the settings name,
    `trunk`, not the clone's unborn `main` (change init-empty-repository, design D5)."""
    init = load_init()
    empty_repository(sandbox)
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    capfd.readouterr()
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    assert "planned onboarding-root:" in capfd.readouterr().out
    assert (sandbox.github.state(), _git_state(sandbox)) == before
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    kinds = sorted(_gh_kind(args) for args in runner.gh())
    assert [kind for kind in kinds if kind != "read"] == ["copy", "issue", "link", "pr"], kinds
    origin = sandbox.origin
    assert not git("for-each-ref", "refs/heads/main", cwd=origin)
    root = git("rev-parse", "trunk", cwd=origin)
    assert git("rev-list", "--parents", "-n", "1", root, cwd=origin) == root
    assert not git("ls-tree", "-r", root, cwd=origin)
    assert git("rev-list", "--count", f"trunk..{BRANCH}", cwd=origin) == "1"
    changed = git("diff", "--name-only", f"trunk..{BRANCH}", cwd=origin)
    assert set(changed.splitlines()) == set(init.OPENSPEC_OUTPUT) | CONSUMER_FILES
    assert [push[-1] for push in _pushes(runner)] == [f"{root}:refs/heads/trunk", BRANCH]
    (pull,) = sandbox.github.pulls
    assert (pull["head"], pull["base"], pull["state"]) == (BRANCH, "trunk", "OPEN")


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
    """Scenarios: Nothing to install — the installation merged into the default branch; Hook
    missing where nothing else is planned — the hook is installed without onboarding."""
    init = load_init()
    _installed(init, sandbox)
    git("switch", "-q", "main", cwd=sandbox.root)
    git("merge", "-q", "--ff-only", BRANCH, cwd=sandbox.root)
    _hook(sandbox).unlink()
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    assert not [label for label in transitions(out) if label.startswith("onboarding-")], out
    assert transitions(out)["pre-push"] == "written", out
    assert init.manual.PRE_COMMIT_ID in _hook(sandbox).read_text(encoding="utf-8")
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


def _unborn_checkout(init: ModuleType, sb: Sandbox) -> None:
    git("update-ref", "-d", "refs/heads/main", cwd=sb.root)


def _empty_dirty(init: ModuleType, sb: Sandbox) -> None:
    empty_repository(sb)
    _dirty(init, sb)


# Each row: arrange the starting point, and what the conflict line names.
UNSAFE: dict[str, tuple[Callable[[ModuleType, Sandbox], None], str]] = {
    "dirty": (_dirty, "git stash"),
    "other-branch": (_other_branch, "git switch main"),
    "branch-not-checked-out": (_branch_on_origin, f"git switch {BRANCH}"),
    "pr-closed": (_pr_closed, "closed"),
    "unpushed-history": (lambda init, sb: empty_origin(sb), "git push -u origin HEAD:trunk"),
    "unborn-checkout": (_unborn_checkout, "git pull origin main"),
    "empty-dirty": (_empty_dirty, "move them out of the worktree"),
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
    assert "``" not in line, line  # no empty branch name
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
        # No listing of the owner's Projects; the manual rows read the linked one by number.
        assert not [
            a for a in runner.gh("api", "graphql") if a[3] == f"query={init.PROJECTS_QUERY}"
        ]
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


# The required workflows a copy keeps enabled (the fake's copy lacks only `Auto-add to project`).
KEPT = ["Item added", "Item reopened", "Item closed", "Pull request merged"]
PROJECT_ROWS = ("project-visibility", "project-workflows", "project-areas")


def _manual_rows(out: str) -> list[str]:
    """The `manual` rows, asserted to end the output."""
    lines = out.splitlines()
    manual = [ln for ln in lines if ln.startswith("manual ")]
    assert manual and lines[-len(manual) :] == manual, lines
    return manual


def _row(manual: list[str], label: str) -> str:
    (row,) = [ln for ln in manual if ln.startswith(f"manual {label}: ")]
    return row


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_manual_actions_are_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    """Scenarios: Manual actions, Machine channel step. A dry-run has no linked Project to read;
    a confirmed run reads the copy it made and linked."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, mode, runner=runner) == 0
    manual = _manual_rows(capfd.readouterr().out)
    visibility, workflows, areas = (_row(manual, label) for label in PROJECT_ROWS)
    assert "visibility" in visibility and "Area" in areas
    if mode == "--confirm":
        assert "Auto-add to project" in workflows, workflows
        assert not [name for name in KEPT if name in workflows], workflows
        assert "cannot read" not in visibility + workflows + areas
    else:
        assert all("(cannot read: " in row for row in (visibility, workflows, areas)), manual
    channel = [ln for ln in manual if ln.startswith("manual plugin-channel: ")]
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
    assert "claude setup-token" in rows[0]
    assert f"gh secret set CLAUDE_CODE_OAUTH_TOKEN -R {CONSUMER}" in rows[0]
    # `_gh_kind` fails on any `gh` command but the reads, the copy and the link: no secret.
    for args in runner.gh():
        _gh_kind(args)


def _plugin_files(sb: Sandbox) -> Path:
    """The machine's plugin files in the observed shapes: the marketplace at `stable` with
    auto-update, the plugin installed at user scope."""
    plugins = sb.home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    source = {"source": "github", "repo": "ekolvah/agent-process-distribution", "ref": "stable"}
    known = {MARKETPLACE: {"source": source, "autoUpdate": True}}
    (plugins / "known_marketplaces.json").write_text(json.dumps(known), encoding="utf-8")
    installed = {"version": 2, "plugins": {PLUGIN: [{"scope": "user", "version": CURRENT}]}}
    (plugins / "installed_plugins.json").write_text(json.dumps(installed), encoding="utf-8")
    return plugins


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_observed_manual_rows_are_omitted(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    """Scenario: Observed done."""
    sandbox.github.secrets.add("CLAUDE_CODE_OAUTH_TOKEN")
    project = sandbox.github.add(linked=CONSUMER)
    project.public, project.areas = True, ["Alpha"]
    project.workflows = {name: True for name in TEMPLATE_WORKFLOWS}
    _plugin_files(sandbox)
    hook = sandbox.root / ".git" / "hooks" / "pre-push"
    hook.parent.mkdir(exist_ok=True)
    hook.write_text(
        "#!/usr/bin/env bash\n# File generated by pre-commit: https://pre-commit.com\n"
        "# ID: 138fd403232d2ddd5efb44317e38bf03\n",
        encoding="utf-8",
    )
    init = load_init()
    assert install(init, sandbox, mode) == 0
    out = capfd.readouterr().out
    manual = _manual_rows(out)
    assert [row.split(":", 1)[0] for row in manual] == ["manual quality-command"], manual
    assert transitions(out)["pre-push"] == "unchanged", out


@pytest.mark.parametrize("case", ["secret-403", "plugin-malformed", "project-read"])
def test_unreadable_manual_state_is_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str
) -> None:
    """Scenario: Unreadable state — the row stays with its reason and the exit code is the
    run's own."""
    mode, fault, labels = {
        "secret-403": ("--dry-run", "secret-list", ["review-secret"]),
        "plugin-malformed": ("--dry-run", "", ["plugin-channel"]),
        "project-read": ("--confirm", "project-read", list(PROJECT_ROWS)),
    }[case]
    if fault:
        sandbox.github.faults[fault] = "fail"
    else:
        (_plugin_files(sandbox) / "known_marketplaces.json").write_text(
            "not json", encoding="utf-8"
        )
    init = load_init()
    assert install(init, sandbox, mode) == 0
    manual = _manual_rows(capfd.readouterr().out)
    for label in labels:
        assert "(cannot read: " in _row(manual, label), manual
    if case == "secret-403":
        assert "HTTP 403" in _row(manual, "review-secret")


# --- this clone's pre-push hook (change init-installs-pre-push-hook) ---------------------

STATUSES = ("planned ", "unchanged ", "written ", "conflict ")


def _hook(sb: Sandbox) -> Path:
    return sb.root / ".git" / "hooks" / "pre-push"


def _hooks(sb: Sandbox) -> set[str]:
    """The clone's hooks other than git's samples."""
    hooks = sb.root / ".git" / "hooks"
    return {p.name for p in hooks.iterdir() if not p.name.endswith(".sample")}


def _is(cmd: list[str], name: str) -> bool:
    return Path(cmd[0]).stem.lower() == name


def test_pre_push_hook_is_installed(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Hook installed in this clone; the `.git/hooks` half of Fresh repository."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--dry-run", runner=runner) == 0
    dry = capfd.readouterr().out
    assert transitions(dry)["pre-push"] == "planned", dry
    assert not _hook(sandbox).exists()
    assert install(init, sandbox, "--confirm", runner=runner) == 0
    out = capfd.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith(STATUSES)]
    assert lines[-2].startswith("written onboarding-pr:"), out
    assert lines[-1].startswith("written pre-push:"), out
    (hooked,) = [i for i, cmd in enumerate(runner.log) if _is(cmd, "pre-commit")]
    assert runner.log[hooked][1:] == ["install", "--hook-type", "pre-push"]
    pushed = [i for i, cmd in enumerate(runner.log) if _is(cmd, "git") and "push" in cmd]
    assert pushed and hooked > max(pushed), runner.log
    assert init.manual.PRE_COMMIT_ID in _hook(sandbox).read_text(encoding="utf-8")
    assert "manual pre-push" not in dry + out
    assert _hooks(sandbox) == {"pre-push"}


def test_sandbox_push_runs_the_local_hook(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """A later run's push goes through the hook the first run installed, and pre-commit
    resolves the hook repository without the network (change hermetic-sandbox-push, D3)."""
    init = load_init()
    record = sandbox.home / "pre-push-ran"
    _installed(init, sandbox)
    assert not record.exists()
    config = sandbox.root / "openspec" / "config.yaml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text.replace("# agent-process:begin\n", "# agent-process:begin\n# stale\n")
        + "# consumer note\n",
        encoding="utf-8",
    )
    capfd.readouterr()
    assert install(init, sandbox, "--confirm") == 0, capfd.readouterr()
    assert record.exists()
    assert git("rev-parse", BRANCH, cwd=sandbox.origin) == git(
        "rev-parse", "HEAD", cwd=sandbox.root
    )


class _NoHookRunner(Runner):
    """`pre-commit` exits 0 and writes nothing."""

    def __call__(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        capture: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if _is([str(cmd[0])], "pre-commit"):
            self.log.append([str(part) for part in cmd])
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return super().__call__(cmd, cwd=cwd, env=env, capture=capture)


def test_pre_push_install_leaves_no_hook(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Install leaves no hook."""
    init = load_init()
    runner = _NoHookRunner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", runner=runner) == 1
    captured = capfd.readouterr()
    assert "written pre-push" not in captured.out, captured.out
    assert str(_hook(sandbox)) in captured.err, captured.err


BLOCKED = {"hooks-path": "core.hooksPath is set", "no-pre-commit": "pre-commit is not on PATH"}


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
@pytest.mark.parametrize("case", list(BLOCKED))
def test_pre_push_blocked_is_manual(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str, mode: str
) -> None:
    """Scenario: Per-clone row."""
    if case == "hooks-path":
        git("config", "core.hooksPath", ".hooks", cwd=sandbox.root)
    else:
        sandbox.which = lambda name: None if name == "pre-commit" else which(name)
    init = load_init()
    assert install(init, sandbox, mode) == 0
    out = capfd.readouterr().out
    assert "pre-push" not in transitions(out), out
    assert not _hook(sandbox).exists()
    assert not (sandbox.root / ".hooks").exists()
    row = _row(_manual_rows(out), "pre-push")
    for part in (
        BLOCKED[case],
        "git config --unset-all core.hooksPath",
        "pre-commit install --hook-type pre-push",
    ):
        assert part in row, row


def test_foreign_pre_push_is_migrated(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Hook installed in this clone — over a hook pre-commit did not install, which
    pre-commit's migration mode keeps (design D3)."""
    foreign = b"#!/bin/sh\nexit 0\n"
    _hook(sandbox).parent.mkdir(exist_ok=True)
    _hook(sandbox).write_bytes(foreign)
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    dry = capfd.readouterr().out
    (line,) = [ln for ln in dry.splitlines() if ln.startswith("planned pre-push:")]
    assert "pre-push.legacy" in line, line
    assert install(init, sandbox, "--confirm") == 0
    out = capfd.readouterr().out
    assert transitions(out)["pre-push"] == "written", out
    assert init.manual.PRE_COMMIT_ID in _hook(sandbox).read_text(encoding="utf-8")
    assert (_hook(sandbox).parent / "pre-push.legacy").read_bytes() == foreign
    assert _hooks(sandbox) == {"pre-push", "pre-push.legacy"}
