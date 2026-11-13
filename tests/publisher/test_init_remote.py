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
    AGENT,
    AGENT_TOKEN,
    ATTRIBUTION,
    BASE_VIEWS,
    BRANCH,
    CONSUMER_FILES,
    CURRENT,
    HOST,
    LABELS,
    LINE,
    MARKETPLACE,
    OWNER,
    PLUGIN,
    REPO_NAME,
    ROOT,
    TEMPLATE_AREAS,
    TEMPLATE_WORKFLOWS,
    TITLE,
    FakeGitHub,
    Runner,
    Sandbox,
    _installed,
    agent_account,
    area_filter,
    check_run,
    empty_origin,
    empty_repository,
    fresh_settings,
    git,
    install,
    load_init,
    local_settings,
    project_settings,
    snapshot,
    transitions,
    user_settings,
    view,
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
    assert settings == {**fresh_settings(), "env": {"OTEL_RESOURCE_ATTRIBUTES": ATTRIBUTION}}


AREA_WRITES = (
    "updateProjectV2Field(",
    "createProjectV2View(",
    "updateProjectV2View(",
    "deleteProjectV2View(",
)


POST_MERGE_WRITES = {
    "rulesets": "ruleset",
    "collaborators/": "collaborator",
    "user/repository_invitations/": "accept",
}


def _post_merge_write(args: list[str]) -> str | None:
    if args[0] == "api" and "-X" in args:
        endpoint = args[args.index("-X") + 2]
        (kind,) = [kind for part, kind in POST_MERGE_WRITES.items() if part in endpoint]
        return kind
    if args[:2] == ["api", "graphql"] and "updateProjectV2Collaborators" in args[-1]:
        return "project-role"
    return None


def _gh_kind(args: list[str]) -> str:
    """`read`, `copy`, `link`, `issue`, `pr`, `areas`, or a post-merge write: `ruleset`,
    `collaborator`, `accept`, `project-role`, `auto-merge`, `pr-edit`; any other `gh`
    command fails the test."""
    reads = (
        ["repo", "view"],
        ["issue", "list"],
        ["pr", "list"],
        ["pr", "view"],
        ["secret", "list"],
        ["variable", "list"],
        ["auth", "status"],
        ["auth", "token"],
    )
    if args[:2] in reads:
        return "read"
    if args[0] == "api" and args[1] != "graphql" and "-X" not in args:
        assert args[-1].startswith((f"repos/{OWNER}/{REPO_NAME}", "user/")), args
        return "read"
    written = _post_merge_write(args)
    if written:
        return written
    if args[:2] == ["api", "graphql"] and not any("mutation" in part for part in args):
        return "read"
    kinds = {
        ("project", "copy"): "copy",
        ("project", "link"): "link",
        ("issue", "create"): "issue",
        ("pr", "create"): "pr",
        ("pr", "edit"): "pr-edit",
        ("repo", "edit"): "auto-merge",
    }
    if tuple(args[:2]) in kinds:
        return kinds[args[0], args[1]]
    if args[:2] == ["api", "graphql"] and any(write in args[3] for write in AREA_WRITES):
        return "areas"
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


@pytest.mark.parametrize("areas", [[], ["--area", "Alpha"]], ids=["no-area", "area"])
def test_dry_run_writes_nothing_remote(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], areas: list[str]
) -> None:
    """Scenario: Dry-run."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    before = sandbox.github.state(), _git_state(sandbox)
    assert install(init, sandbox, "--dry-run", *areas, runner=runner) == 0
    assert runner.gh("repo", "view") and runner.gh("api", "graphql")
    assert {_gh_kind(args) for args in runner.gh()} == {"read"}
    assert (sandbox.github.state(), _git_state(sandbox)) == before
    if areas:
        lines = capfd.readouterr().out.splitlines()
        (line,) = [ln for ln in lines if ln.startswith("planned project-areas: ")]
        _, dropped = line.split("Alpha", 1)
        assert all(name in dropped for name in TEMPLATE_AREAS), line


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
    """Scenario: Rerun after the merge — still on the installation branch, with protection
    active and no agent account, so no post-merge transition writes."""
    init = load_init()
    _installed(init, sandbox)
    sandbox.github.required_checks = list(PROCESS_CHECKS)
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
        assert seen == dict.fromkeys(LABELS, "written") | {"protection": "after-merge"} | {
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
PROJECT_ROWS = ("project-workflows", "project-areas")
PROCESS_CHECKS = ("agent-process / quality", "agent-review / agent-review")


def _manual_rows(out: str) -> list[str]:
    """The `manual` rows, asserted to end the output."""
    lines = out.splitlines()
    manual = [ln for ln in lines if ln.startswith("manual ")]
    assert lines[len(lines) - len(manual) :] == manual, lines
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
    workflows, areas = (_row(manual, label) for label in PROJECT_ROWS)
    assert "Area" in areas and "--area" in areas
    if mode == "--confirm":
        assert "Auto-add to project" in workflows, workflows
        assert not [name for name in KEPT if name in workflows], workflows
        assert "cannot read" not in workflows + areas
    else:
        assert all("(cannot read: " in row for row in (workflows, areas)), manual
    channel = [ln for ln in manual if ln.startswith("manual plugin-channel: ")]
    assert len(channel) == 1, channel
    add = 'claude plugin marketplace add "ekolvah/agent-process-distribution#stable"'
    write = '"autoUpdate": true'
    assert "~/.claude/settings.json" in channel[0] and "/plugin" not in channel[0], channel
    steps = [channel[0].index(s) for s in (add, f"claude plugin install {PLUGIN}", write)]
    assert steps == sorted(steps), channel
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


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_readings_prerequisites_are_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    """Scenario: Readings prerequisites."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, mode, runner=runner) == 0
    row = _row(_manual_rows(capfd.readouterr().out), "task-readings")
    assert f"https://github.com/{CONSUMER}/settings/variables/actions" in row
    assert f"gh variable set GRAFANA_URL -R {CONSUMER}" in row
    assert f"gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R {CONSUMER}" in row
    assert f"agent-process dashboard {CONSUMER}" in row
    assert "Dashboards → New → Import" in row
    assert row.endswith("(not found: grafana MCP server in ~/.claude.json)"), row
    # `_gh_kind` fails on any `gh` command but the reads, the copy and the link: no write.
    for args in runner.gh():
        _gh_kind(args)


@pytest.mark.parametrize(
    ("mode", "settings", "named"),
    [
        *[
            pytest.param(mode, settings, "GH_TOKEN", id=f"{mode}-{name}")
            for mode in ("--dry-run", "--confirm")
            for name, settings in (("absent", None), ("no-env", {"permissions": {}}))
        ],
        pytest.param("--dry-run", {"env": {"GH_TOKEN": "person-token"}}, "ADMIN", id="admin"),
        pytest.param("--dry-run", {"env": {"GH_TOKEN": "stranger-token"}}, "READ", id="read"),
    ],
)
def test_agent_identity_pending_is_manual(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str, settings: Any, named: str
) -> None:
    """Scenario: Identity pending — without an agent account in `gh auth status`."""
    sandbox.github.permissions.update({"person-token": "ADMIN", "stranger-token": "READ"})
    if settings is not None:
        local_settings(sandbox, text=json.dumps(settings))
    init = load_init()
    assert install(init, sandbox, mode) == 0
    row = _row(_manual_rows(capfd.readouterr().out), "agent-identity")
    assert "(cannot read: " not in row, row
    assert named in row and init.manual.IDENTITY_FIX in row, row
    assert "gh auth login -s project,workflow" in row and "agent-process init" in row, row


def test_agent_identity_holds(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario: Identity holds — read with the settings' token, not the session's."""
    monkeypatch.setenv("GH_TOKEN", "person-token")
    local_settings(sandbox, "agent-token")
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    manual = _manual_rows(capfd.readouterr().out)
    assert not [ln for ln in manual if ln.startswith("manual agent-identity: ")], manual
    tokened = [args for token, args in sandbox.github.tokened if token == "agent-token"]
    assert len(tokened) == 1 and tokened[0][:2] == ["api", "graphql"], tokened
    assert "viewerPermission" in tokened[0][-1] and "mutation" not in tokened[0][-1], tokened


# --- the post-merge steps (change init-runs-post-merge-steps) ----------------------------

POST_MERGE = [
    "protection",
    "agent-collaborator",
    "agent-project",
    "approval-ruleset",
    "auto-merge",
    "agent-token",
]
TEMPLATES = ROOT / "skills" / "agent-process" / "templates"
APPROVAL = json.loads((TEMPLATES / "approval_ruleset.json").read_text(encoding="utf-8"))
PROCESS_RULESET = json.loads((TEMPLATES / "ruleset.json").read_text(encoding="utf-8"))
SETTINGS_LOCAL = Path(".claude") / "settings.local.json"
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
    local_settings(sb, AGENT_TOKEN)


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
    local_settings(sandbox, text='{\n    "permissions": {"allow": ["Bash(ls)"]}\n}\n')
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
    settings = json.loads((sandbox.root / SETTINGS_LOCAL).read_text(encoding="utf-8"))
    assert settings == {"permissions": {"allow": ["Bash(ls)"]}, "env": {"GH_TOKEN": AGENT_TOKEN}}
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


def _settings_not_ignored(sb: Sandbox) -> None:
    path = sb.root / SETTINGS_LOCAL
    path.parent.mkdir(exist_ok=True)
    path.write_text('{"permissions": {}}\n', encoding="utf-8")


@pytest.mark.parametrize(
    ("arrange", "reason"),
    [
        pytest.param(_settings_not_ignored, "not ignored", id="not-ignored"),
        pytest.param(lambda sb: local_settings(sb, text="[]"), "JSON object", id="not-object"),
    ],
)
def test_post_merge_agent_token_conflict(
    sandbox: Sandbox,
    capfd: pytest.CaptureFixture[str],
    arrange: Callable[[Sandbox], None],
    reason: str,
) -> None:
    """Scenario: Token file not ignored — or not a JSON object; the file stays as it was."""
    init = load_init()
    agent_account(sandbox)
    _merged(init, sandbox)
    arrange(sandbox)
    before = (sandbox.root / SETTINGS_LOCAL).read_bytes()
    runner = Runner(init, HOST, sandbox.github)
    capfd.readouterr()
    assert install(init, sandbox, "--confirm", runner=runner) == 2
    out = capfd.readouterr().out
    (line,) = [ln for ln in out.splitlines() if ln.startswith("conflict agent-token: ")]
    assert reason in line and AGENT_TOKEN not in out, line
    assert (sandbox.root / SETTINGS_LOCAL).read_bytes() == before
    assert _non_reads(runner) == []


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


def _plugin_files(sb: Sandbox, auto_update: bool | None = True) -> Path:
    """The machine's plugin files in the observed shapes: the marketplace at `stable` with
    `auto_update` (`None` leaves the key out), the plugin installed at user scope."""
    plugins = sb.home / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    source = {"source": "github", "repo": "ekolvah/agent-process-distribution", "ref": "stable"}
    entry: dict[str, object] = {"source": source}
    if auto_update is not None:
        entry["autoUpdate"] = auto_update
    known = {MARKETPLACE: entry}
    (plugins / "known_marketplaces.json").write_text(json.dumps(known), encoding="utf-8")
    installed = {"version": 2, "plugins": {PLUGIN: [{"scope": "user", "version": CURRENT}]}}
    (plugins / "installed_plugins.json").write_text(json.dumps(installed), encoding="utf-8")
    return plugins


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_observed_manual_rows_are_omitted(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    """Scenario: Observed done."""
    attribution = f"service.version=1, vcs.repository.name={CONSUMER}"
    project_settings(sandbox, {"env": {"OTEL_RESOURCE_ATTRIBUTES": attribution}})
    sandbox.github.secrets.update({"CLAUDE_CODE_OAUTH_TOKEN", "GRAFANA_SERVICE_ACCOUNT_TOKEN"})
    sandbox.github.variables["GRAFANA_URL"] = "https://stack.grafana.net"
    project = sandbox.github.add(linked=CONSUMER)
    project.areas = ["Alpha"]
    project.workflows = {name: True for name in TEMPLATE_WORKFLOWS}
    _plugin_files(sandbox)
    local_settings(sandbox, "agent-token")
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
    assert manual == [], manual
    assert transitions(out)["pre-push"] == "unchanged", out


@pytest.mark.parametrize(
    ("settings", "known", "row"), [(True, None, False), (False, True, True), (None, True, False)]
)
def test_plugin_channel_readsuser_settings(
    sandbox: Sandbox,
    capfd: pytest.CaptureFixture[str],
    settings: bool | None,
    known: bool | None,
    row: bool,
) -> None:
    """Scenario: Auto-update read from user settings. `None` drops the key, the state
    `marketplace add` leaves."""
    _plugin_files(sandbox, auto_update=known)
    entry = {} if settings is None else {"autoUpdate": settings}
    user_settings(sandbox, json.dumps({"extraKnownMarketplaces": {MARKETPLACE: entry}}))
    init = load_init()
    assert install(init, sandbox, "--dry-run") == 0
    manual = _manual_rows(capfd.readouterr().out)
    channel = [ln for ln in manual if ln.startswith("manual plugin-channel: ")]
    assert bool(channel) is row, manual
    assert not [ln for ln in channel if "(cannot read: " in ln], channel


def _user_settings_malformed(sb: Sandbox) -> None:
    _plugin_files(sb)
    user_settings(sb, "not json")


# --- the areas transition ---------------------------------------------------------------


def _areas_of(sb: Sandbox) -> tuple[list[str] | None, dict[str, str | None], int]:
    """The linked Project's `Area` options, its views' filters by name, and its view count."""
    (project,) = [p for p in sb.github.projects if CONSUMER in p.repositories]
    filters = {v["name"]: v["filter"] for v in project.views}
    return project.areas, filters, len(project.views)


def test_areas_replace_the_template(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Copy gets the consumer's areas."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    flags = ["--area", "Alpha", "--area", "Beta Two"]
    assert install(init, sandbox, "--confirm", *flags, runner=runner) == 0
    out = capfd.readouterr().out
    areas = {name: area_filter(name) for name in ("Alpha", "Beta Two")}
    assert _areas_of(sandbox) == (["Alpha", "Beta Two"], {**BASE_VIEWS, **areas}, 5)
    kinds = sorted(_gh_kind(args) for args in runner.gh())
    writes = [kind for kind in kinds if kind not in {"read", "areas"}]
    assert writes == ["copy", "issue", "link", "pr"] and "areas" in kinds, kinds
    assert transitions(out)["project-areas"] == "written", out
    assert "manual project-areas: " not in out, out


def test_areas_spare_a_non_area_view_of_the_copy(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str]
) -> None:
    """Scenario: Copy keeps its other views — the copy's views are read only when the step
    writes, so a given area named after one of its other views fails the step."""
    init = load_init()
    assert install(init, sandbox, "--confirm", "--area", "Bugs") == 1
    err = capfd.readouterr().err
    assert "project-areas: " in err and "not area views: Bugs" in err, err
    views = {**BASE_VIEWS, **{name: area_filter(name) for name in TEMPLATE_AREAS}}
    assert _areas_of(sandbox) == (TEMPLATE_AREAS, views, len(views))


def test_areas_retry_completes_views(sandbox: Sandbox, capfd: pytest.CaptureFixture[str]) -> None:
    """Scenario: Retry completes the views — a run that wrote the view `Alpha` but not its
    filter, the other views or the options."""
    project = sandbox.github.add(linked=CONSUMER)
    project.views.append(view("Alpha", None))
    init = load_init()
    assert install(init, sandbox, "--confirm", "--area", "Alpha") == 0
    out = capfd.readouterr().out
    assert "planned project-areas: " in out, out
    assert _areas_of(sandbox) == (["Alpha"], {**BASE_VIEWS, "Alpha": area_filter("Alpha")}, 4)


def _own(sb: Sandbox) -> None:
    sb.github.add(linked=CONSUMER).areas = ["Own"]


def _template_linked(sb: Sandbox) -> None:
    sb.github.projects[0].repositories.add(CONSUMER)


def _no_area_field(sb: Sandbox) -> None:
    sb.github.add(linked=CONSUMER).areas = None


def _foreign_view(sb: Sandbox) -> None:
    sb.github.add(linked=CONSUMER).views.append(view("Alpha", "label:bug"))


@pytest.mark.parametrize(
    "arrange",
    [_own, _template_linked, _no_area_field, _foreign_view],
    ids=["own", "template", "no-field", "foreign-view"],
)
def test_areas_not_replaced(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], arrange: Callable[[Sandbox], None]
) -> None:
    """Scenario: Areas not replaced."""
    arrange(sandbox)
    before = _areas_of(sandbox)
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    assert install(init, sandbox, "--confirm", "--area", "Alpha", runner=runner) == 0
    out = capfd.readouterr().out
    assert transitions(out)["project-areas"] == "unchanged", out
    assert "areas" not in {_gh_kind(args) for args in runner.gh()}
    assert _areas_of(sandbox) == before
    if arrange in (_own, _template_linked):
        assert "manual project-areas: " not in out, out
    else:
        row = _row(_manual_rows(out), "project-areas")
        assert ("--area" in row) is (arrange is _foreign_view), row


@pytest.mark.parametrize(
    "names", [[""], ['a"b'], ["Alpha", "Alpha"]], ids=["empty", "quote", "repeated"]
)
def test_invalid_area_exits_2(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], names: list[str]
) -> None:
    """Scenario: Invalid area — argparse names `--area`, not an unrecognized argument."""
    init = load_init()
    runner = Runner(init, HOST, sandbox.github)
    flags = [part for name in names for part in ("--area", name)]
    assert install(init, sandbox, "--dry-run", *flags, runner=runner) == 2
    assert "error: argument --area: " in capfd.readouterr().err
    assert runner.log == []


def _fault(name: str) -> Callable[[Sandbox], None]:
    return lambda sb: sb.github.faults.update({name: "fail"})


def _malformed_plugin(sb: Sandbox) -> None:
    (_plugin_files(sb) / "known_marketplaces.json").write_text("not json", encoding="utf-8")


UNREADABLE: dict[str, tuple[str, Callable[[Sandbox], object], list[str]]] = {
    "secret-403": ("--dry-run", _fault("secret-list"), ["review-secret", "task-readings"]),
    "variable-403": ("--dry-run", _fault("variable-list"), ["task-readings"]),
    "plugin-malformed": ("--dry-run", _malformed_plugin, ["plugin-channel"]),
    "user-settings-malformed": (
        "--dry-run",
        _user_settings_malformed,
        ["plugin-channel", "telemetry-attribution"],
    ),
    "project-read": ("--confirm", _fault("project-read"), list(PROJECT_ROWS)),
    "settings-malformed": (
        "--dry-run",
        lambda sb: local_settings(sb, text="not json"),
        ["agent-identity"],
    ),
    "settings-shape": (
        "--dry-run",
        lambda sb: local_settings(sb, text='{"env": []}'),
        ["agent-identity"],
    ),
    "project-settings-shape": (
        "--dry-run",
        lambda sb: project_settings(sb, {"env": []}),
        ["telemetry-attribution"],
    ),
    "project-settings-value": (
        "--dry-run",
        lambda sb: project_settings(sb, {"env": {"OTEL_RESOURCE_ATTRIBUTES": 1}}),
        ["telemetry-attribution"],
    ),
}


@pytest.mark.parametrize("case", list(UNREADABLE))
def test_unreadable_manual_state_is_printed(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], case: str
) -> None:
    """Scenario: Unreadable state — the row stays with its reason and the exit code is the
    run's own. The sandbox is not an empty repository, so `init` itself never reads
    `repos/<owner>/<name>`."""
    mode, arrange, labels = UNREADABLE[case]
    arrange(sandbox)
    init = load_init()
    assert install(init, sandbox, mode) == 0
    manual = _manual_rows(capfd.readouterr().out)
    for label in labels:
        assert "(cannot read: " in _row(manual, label), manual
    if case.endswith("-403"):
        for label in labels:
            assert "HTTP 403" in _row(manual, label)


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
        input: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if _is([str(cmd[0])], "pre-commit"):
            self.log.append([str(part) for part in cmd])
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return super().__call__(cmd, cwd=cwd, env=env, capture=capture, input=input)


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
    assert "repo: local" not in row, row


@pytest.mark.parametrize("mode", ["--dry-run", "--confirm"])
def test_pre_push_names_existing_hooks(
    sandbox: Sandbox, capfd: pytest.CaptureFixture[str], mode: str
) -> None:
    """Scenario: Per-clone row over existing hooks."""
    git("config", "core.hooksPath", ".hooks", cwd=sandbox.root)
    hooks = sandbox.root / ".hooks"
    hooks.mkdir()
    (hooks / "commit-msg").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (hooks / "pre-push.sample").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    git("add", ".hooks", cwd=sandbox.root)
    git("commit", "-q", "-m", "ship hooks", cwd=sandbox.root)
    init = load_init()
    assert install(init, sandbox, mode) == 0
    out = capfd.readouterr().out
    assert "pre-push" not in transitions(out), out
    assert sorted(p.name for p in hooks.iterdir()) == ["commit-msg", "pre-push.sample"]
    assert not _hook(sandbox).exists()
    row = _row(_manual_rows(out), "pre-push")
    for part in (
        str(hooks),
        "commit-msg",
        "stops running",
        ".pre-commit-config.yaml",
        "repo: local",
        "git config --unset-all core.hooksPath",
        "pre-commit install --hook-type pre-push",
    ):
        assert part in row, row
    assert "pre-push.sample" not in row, row


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
