"""Delivery scripts of the OpenSpec apply loop (change v2-1a-delivery-scripts).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
_PROJECT = {"id": "PVT_1", "number": 4, "title": "Board", "resourcePath": "/users/owner/projects/4"}
_FIELDS = {
    "fields": [
        {
            "id": "F_STATUS",
            "name": "Status",
            "type": "ProjectV2SingleSelectField",
            "options": [
                {"id": "S_TODO", "name": "Todo"},
                {"id": "S_PROG", "name": "In Progress"},
            ],
        },
        {
            "id": "F_PRIO",
            "name": "Priority",
            "type": "ProjectV2SingleSelectField",
            "options": [{"id": "P_HIGH", "name": "High"}, {"id": "P_LOW", "name": "Low"}],
        },
    ]
}


def _script(name: str) -> Any:
    return importlib.import_module(f"scripts.{name}")


class _Gh:
    """Fake `gh`: answers by command shape, records every call."""

    def __init__(self, *, projects: list[dict] | None = None) -> None:
        self.calls: list[list[str]] = []
        self.projects = [_PROJECT] if projects is None else projects

    def __call__(self, cmd: list[str]) -> str:
        self.calls.append(cmd)
        head = cmd[:3]
        if head == ["gh", "repo", "view"]:
            # `Nodes` with a capital N is what gh 2.87.3 prints for `--json projectsV2`.
            return json.dumps(
                {
                    "owner": {"login": "owner"},
                    "name": "repo",
                    "projectsV2": {"Nodes": self.projects},
                }
            )
        if head == ["gh", "issue", "view"]:
            return json.dumps({"url": "https://github.com/owner/repo/issues/7"})
        if head == ["gh", "api", "graphql"]:
            raise AssertionError("set_status must read the linked Project with gh repo view")
        if head == ["gh", "project", "field-list"]:
            return json.dumps(_FIELDS)
        if head == ["gh", "project", "item-add"]:
            return json.dumps({"id": "PVTI_7"})
        if head == ["gh", "project", "item-edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {cmd}")

    def edits(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["gh", "project", "item-edit"]]


def test_behavioural_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Behavioural change — `check_red --report` reads the runner's report, spawns nothing."""
    check_red = _script("check_red")

    def no_spawn(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("--report must not spawn pytest")

    monkeypatch.setattr(check_red.subprocess, "run", no_spawn)
    red = tmp_path / "red.xml"
    red.write_text(
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_a">'
        '<failure message="boom"/></testcase></testsuite></testsuites>',
        encoding="utf-8",
    )
    green = tmp_path / "green.xml"
    green.write_text(
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_a"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    check_red.main(["--report", str(red), "tests/publisher/test_x.py::test_a"])
    with pytest.raises(SystemExit) as exc:
        check_red.main(["--report", str(green), "tests/publisher/test_x.py::test_a"])
    assert exc.value.code == 1


def test_class_scoped_node_id(tmp_path: Path) -> None:
    """A node id ending in a test class selects every test of that class, nested classes included."""
    check_red = _script("check_red")
    report = tmp_path / "red.xml"
    report.write_text(
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x.TestA" name="test_a">'
        '<failure message="boom"/></testcase>'
        '<testcase classname="tests.publisher.test_x.TestA.TestInner" name="test_b">'
        '<failure message="boom"/></testcase>'
        '<testcase classname="tests.publisher.test_x" name="test_other"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    check_red.main(["--report", str(report), "tests/publisher/test_x.py::TestA"])
    with pytest.raises(SystemExit) as exc:
        check_red.main(["--report", str(report), "tests/publisher/test_x.py::TestB"])
    assert exc.value.code == 1


def test_parametrized_node_id(tmp_path: Path) -> None:
    """`::` inside a parameter id is part of the id, not a class delimiter."""
    check_red = _script("check_red")
    report = tmp_path / "red.xml"
    report.write_text(
        '<testsuites><testsuite><testcase classname="tests.publisher.test_x" name="test_p[a::b]">'
        '<failure message="boom"/></testcase>'
        '<testcase classname="tests.publisher.test_x" name="test_p[c]"/>'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )
    check_red.main(["--report", str(report), "tests/publisher/test_x.py::test_p[a::b]"])


def test_tracking_issue_created() -> None:
    """Scenario: Tracking issue created — names resolve to ids, item-edit carries them."""
    set_status = _script("set_status")
    gh = _Gh()

    set_status.set_status(7, "In Progress", priority="High", gh=gh)

    edits = gh.edits()
    assert len(edits) == 2
    for cmd, field_id, option_id in zip(edits, ["F_STATUS", "F_PRIO"], ["S_PROG", "P_HIGH"]):
        assert cmd[cmd.index("--id") + 1] == "PVTI_7"
        assert cmd[cmd.index("--field-id") + 1] == field_id
        assert cmd[cmd.index("--project-id") + 1] == "PVT_1"
        assert cmd[cmd.index("--single-select-option-id") + 1] == option_id
    assert not any(c[:2] == ["gh", "api"] for c in gh.calls)


def test_priority_field_drift(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Priority field drift — unknown option → exit 2 listing the options, nothing changed."""
    set_status = _script("set_status")
    gh = _Gh()

    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress", "--priority", "Urgent"], gh=gh)

    assert exc.value.code == 2
    assert gh.edits() == []
    err = capsys.readouterr().err
    assert "Urgent" in err and "High" in err and "Low" in err


def test_priority_only() -> None:
    """Scenario: Priority only — Status is optional; nothing given at all is a usage error."""
    set_status = _script("set_status")
    gh = _Gh()

    set_status.main(["7", "--priority", "High"], gh=gh)

    edits = gh.edits()
    assert len(edits) == 1
    assert edits[0][edits[0].index("--field-id") + 1] == "F_PRIO"
    assert edits[0][edits[0].index("--single-select-option-id") + 1] == "P_HIGH"

    gh = _Gh()
    with pytest.raises(SystemExit) as exc:
        set_status.main(["7"], gh=gh)
    assert exc.value.code == 2
    assert gh.edits() == []


def test_linked_project_of_another_owner() -> None:
    """The Project's owner comes from its resourcePath, not from the repository's owner."""
    set_status = _script("set_status")
    gh = _Gh(projects=[{**_PROJECT, "resourcePath": "/orgs/acme/projects/4"}])

    set_status.set_status(7, "In Progress", gh=gh)

    owners = [c[c.index("--owner") + 1] for c in gh.calls if "--owner" in c]
    assert owners and set(owners) == {"acme"}


def test_several_linked_projects(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Several linked Projects — zero or several linked Projects → exit 2 naming them."""
    set_status = _script("set_status")
    gh = _Gh(projects=[_PROJECT, {"id": "PVT_2", "number": 5, "title": "Other"}])

    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress"], gh=gh)

    assert exc.value.code == 2
    assert gh.edits() == []
    err = capsys.readouterr().err
    assert "#4 Board" in err and "#5 Other" in err

    gh = _Gh(projects=[])
    with pytest.raises(SystemExit) as exc:
        set_status.main(["7", "In Progress"], gh=gh)
    assert exc.value.code == 2
    assert gh.edits() == []


def _rollup(*checks: tuple[str, str, str | None], head: str = "abc123") -> str:
    return json.dumps(
        {
            "headRefOid": head,
            "url": "https://github.com/owner/repo/pull/9",
            "statusCheckRollup": [
                {
                    "__typename": "CheckRun",
                    "name": name,
                    "workflowName": name,
                    "status": status,
                    "conclusion": conclusion,
                    "detailsUrl": f"https://ci.test/{name}",
                }
                for name, status, conclusion in checks
            ],
        }
    )


def _threads(*unresolved: str, head: str = "abc123") -> str:
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
                        "headRefOid": head,
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False},
                            "nodes": [
                                {
                                    "id": f"T_{i}",
                                    "isResolved": False,
                                    "path": path,
                                    "line": 1,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "author": {"login": "reviewer"},
                                                "body": f"fix {path}",
                                                "url": f"https://github.com/t/{i}",
                                            }
                                        ]
                                    },
                                }
                                for i, path in enumerate(unresolved)
                            ],
                        },
                    }
                }
            }
        }
    )


class _Sequence:
    """Fake `gh` for `wait_for_pr`: one rollup per poll, one thread payload per query."""

    def __init__(self, rollups: list[str], threads: str | list[str]) -> None:
        self.rollups = list(rollups)
        self.threads = [threads] if isinstance(threads, str) else list(threads)
        self.polls = 0

    def __call__(self, cmd: list[str]) -> str:
        if cmd[:3] == ["gh", "pr", "view"]:
            self.polls += 1
            return self.rollups.pop(0) if len(self.rollups) > 1 else self.rollups[0]
        if cmd[:3] == ["gh", "repo", "view"]:
            return json.dumps({"owner": {"login": "owner"}, "name": "repo"})
        if cmd[:3] == ["gh", "api", "graphql"]:
            return self.threads.pop(0) if len(self.threads) > 1 else self.threads[0]
        raise AssertionError(f"unexpected gh call: {cmd}")


def test_pending_review(capsys: pytest.CaptureFixture[str]) -> None:
    """Scenario: Pending review — a running check is pending; red or unresolved → 1; clean → 0; timeout → 3."""
    wait_for_pr = _script("wait_for_pr")
    green = ("quality", "COMPLETED", "SUCCESS")
    running = ("agent-review", "IN_PROGRESS", None)
    red = ("agent-review", "COMPLETED", "FAILURE")
    done = ("agent-review", "COMPLETED", "SUCCESS")

    def run(rollups: list[str], threads: str, *, timeout: int = 1800) -> tuple[int, str]:
        gh = _Sequence(rollups, threads)
        ticks = iter(range(0, 10_000, 60))
        code = wait_for_pr.wait_for_pr(
            9, gh=gh, clock=lambda: next(ticks), sleep=lambda s: None, timeout=timeout
        )
        return code, capsys.readouterr().out

    code, out = run([_rollup(green, running), _rollup(green, red)], _threads())
    assert code == 1 and "agent-review" in out

    code, out = run([_rollup(green, done)], _threads("docs/a.md"))
    assert code == 1 and "docs/a.md" in out

    code, out = run([_rollup(green, done)], _threads())
    assert code == 0

    code, out = run([_rollup(green, running)], _threads(), timeout=120)
    assert code == 3 and "timeout" in out.lower()

    # Right after a push the rollup is empty until the workflows attach: pending, not clean.
    code, out = run([_rollup(), _rollup(green, done)], _threads())
    assert code == 0
    code, out = run([_rollup()], _threads(), timeout=120)
    assert code == 3 and "no checks" in out.lower()

    # A concluded rollup counts only once two consecutive polls list the same checks: a
    # workflow that attaches late must not be missed behind a fast one that already passed.
    gh = _Sequence([_rollup(green), _rollup(green, running), _rollup(green, done)], _threads())
    ticks = iter(range(0, 10_000, 60))
    code = wait_for_pr.wait_for_pr(9, gh=gh, clock=lambda: next(ticks), sleep=lambda s: None)
    assert code == 0 and gh.polls == 4

    # A new head between the two polls restarts the settling: its fast check must not be
    # confirmed by the previous head's poll.
    gh = _Sequence(
        [_rollup(green), _rollup(green, head="def456"), _rollup(green, running, head="def456")],
        _threads(),
    )
    ticks = iter(range(0, 10_000, 60))
    code = wait_for_pr.wait_for_pr(
        9, gh=gh, clock=lambda: next(ticks), sleep=lambda s: None, timeout=240
    )
    assert code == 3 and "def456" in capsys.readouterr().out

    # A push between the settled poll and the thread query: the threads answer names the
    # new head, so the settling restarts on it instead of reporting the old head clean.
    abc, done_def = _rollup(green, done), _rollup(green, done, head="def456")
    gh = _Sequence([abc, abc, done_def], _threads(head="def456"))
    ticks = iter(range(0, 10_000, 60))
    code = wait_for_pr.wait_for_pr(9, gh=gh, clock=lambda: next(ticks), sleep=lambda s: None)
    assert code == 0 and gh.polls == 4 and "def456" in capsys.readouterr().out
    gh = _Sequence([abc, abc, _rollup(green, running, head="def456")], _threads(head="def456"))
    ticks = iter(range(0, 10_000, 60))
    code = wait_for_pr.wait_for_pr(
        9, gh=gh, clock=lambda: next(ticks), sleep=lambda s: None, timeout=300
    )
    assert code == 3 and "def456" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("script", "attr"),
    [("set_status", "run_gh"), ("wait_for_pr", "run_gh"), ("archive_change", "_runner")],
)
def test_none_capture_is_an_error(monkeypatch: pytest.MonkeyPatch, script: str, attr: str) -> None:
    """AGENTS.md: a `None` stdout or stderr is a broken capture, never an empty string."""
    module = _script(script)

    class _Completed:
        returncode = 0
        stdout = None
        stderr = None

    monkeypatch.setattr(module.subprocess, "run", lambda *a, **k: _Completed())
    runner = getattr(module, attr)
    if attr == "_runner":
        runner = runner(Path("."))
    with pytest.raises(RuntimeError, match="capture"):
        runner(["gh", "repo", "view"])


def test_archive_commit(tmp_path: Path) -> None:
    """Scenarios: Archive commit, Stale archive lock."""
    archive_change = _script("archive_change")
    change = "v2-9-example"
    change_dir = tmp_path / "openspec" / "changes" / change
    change_dir.mkdir(parents=True)
    archive = tmp_path / "openspec" / "changes" / "archive"
    archive.mkdir()
    lock = archive / ".openspec-archive.lock"
    tasks = change_dir / "tasks.md"
    # The own task's command sits on a continuation line (as on #124's task 4.3).
    tasks.write_text(
        "- [x] 1.1 done\n"
        "- [ ] 4.1 `git status --short` empty;\n"
        f"  `python .agent-process/scripts/archive_change.py {change}` archives, commits, pushes.\n"
        "- [ ] 4.2 `gh pr create`; the person merges.\n",
        encoding="utf-8",
    )
    order: list[str] = []
    status = ""

    def run(cmd: list[str]) -> str:
        if "archive" in cmd:
            order.append("archive")
            text = tasks.read_text(encoding="utf-8")
            assert "- [x] 4.1" in text and "- [ ] 4.2" in text
            (archive / f"2026-01-01-{change}").mkdir()
            tasks.replace(archive / f"2026-01-01-{change}" / "tasks.md")
            lock.write_text("", encoding="utf-8")
            return ""
        if cmd[:2] == ["git", "commit"]:
            order.append("commit")
            assert not lock.exists()
            return ""
        if cmd[:2] == ["git", "push"]:
            order.append("push")
            return ""
        if cmd[:2] == ["git", "add"]:
            return ""
        if cmd[:2] == ["git", "status"]:
            return status
        raise AssertionError(f"unexpected call: {cmd}")

    # No review request and no wait: the PR does not exist yet when the archive lands.
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 0
    assert order == ["archive", "commit", "push"]

    # Scenario: Stale archive lock — a lock left by an interrupted run stops the script.
    lock.write_text("", encoding="utf-8")
    order.clear()
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert order == []

    # Scenario: Archive commit — the worktree must be clean before the archive; a stray edit
    # would be left behind the pushed head, so the script stops instead of committing openspec/.
    lock.unlink()
    status = " M .agent-process/scripts/wait_for_pr.py\n"
    assert archive_change.archive_change(change, root=tmp_path, run=run) == 2
    assert order == []
