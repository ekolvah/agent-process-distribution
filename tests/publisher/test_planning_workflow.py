"""Planning and implementation run on the OpenSpec skills (change v2-1-planning-workflow).

One test per scenario of the change's spec deltas that a script can prove; the
scenario name is the test name. Scripts are imported inside the tests so that a
missing script fails its own scenario instead of erroring the whole module at
collection (``check_red`` counts a collection error as "not RED").
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "openspec" / "schemas" / "agent-process" / "schema.yaml"
CONFIG = ROOT / "openspec" / "config.yaml"

# v1 planner and implementer entry points that the change removes (root-only after v2-0b).
_V1_ENTRY_POINTS = (
    "commands/plan.md",
    "commands/implement.md",
    "agents/discovery.md",
    ".agents/skills/plan-issue",
    ".agents/skills/implement-issue",
    ".agents/orchestration/change-classes.yaml",
    ".agent-process/scripts/validate_issue_sections.py",
    ".agent-process/scripts/capture_external_fixture.py",
    ".agent-process/scripts/check_fixture_ratchet.py",
    "tests/agent_process/test_validate_issue_status.py",
)

_PROJECT = {"id": "PVT_1", "number": 4, "title": "Board"}
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
            return json.dumps({"owner": {"login": "owner"}, "name": "repo"})
        if head == ["gh", "api", "graphql"]:
            return json.dumps({"data": {"repository": {"projectsV2": {"nodes": self.projects}}}})
        if head == ["gh", "issue", "view"]:
            return json.dumps({"url": "https://github.com/owner/repo/issues/7", "projectItems": []})
        if head == ["gh", "project", "field-list"]:
            return json.dumps(_FIELDS)
        if head == ["gh", "project", "item-add"]:
            return json.dumps({"id": "PVTI_7"})
        if head == ["gh", "project", "item-edit"]:
            return ""
        raise AssertionError(f"unexpected gh call: {cmd}")

    def edits(self) -> list[list[str]]:
        return [c for c in self.calls if c[:3] == ["gh", "project", "item-edit"]]


def test_roles_and_carriers() -> None:
    """Scenarios: Procedure changes once, Label change."""
    schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
    assert [a["id"] for a in schema["artifacts"]] == [
        "proposal",
        "specs",
        "design",
        "architect-review",
        "tasks",
    ]
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["schema"] == "agent-process"
    rules = config["rules"]
    assert {"proposal", "tasks", "architect-review"} <= set(rules)
    assert set(rules) <= {a["id"] for a in schema["artifacts"]}
    present = [p for p in _V1_ENTRY_POINTS if (ROOT / p).exists()]
    assert present == []


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


def _rollup(*checks: tuple[str, str, str | None]) -> str:
    return json.dumps(
        {
            "headRefOid": "abc123",
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


def _threads(*unresolved: str) -> str:
    return json.dumps(
        {
            "data": {
                "repository": {
                    "pullRequest": {
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
                        }
                    }
                }
            }
        }
    )


class _Sequence:
    """Fake `gh` for `wait_for_pr`: one rollup per poll, then the thread payload."""

    def __init__(self, rollups: list[str], threads: str) -> None:
        self.rollups = list(rollups)
        self.threads = threads
        self.polls = 0

    def __call__(self, cmd: list[str]) -> str:
        if cmd[:3] == ["gh", "pr", "view"]:
            self.polls += 1
            return self.rollups.pop(0) if len(self.rollups) > 1 else self.rollups[0]
        if cmd[:3] == ["gh", "repo", "view"]:
            return json.dumps({"owner": {"login": "owner"}, "name": "repo"})
        if cmd[:3] == ["gh", "api", "graphql"]:
            return self.threads
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


def test_archive_commit(tmp_path: Path) -> None:
    """Scenarios: Archive commit, Stale archive lock, Behaviour change."""
    finish_change = _script("finish_change")
    change = "v2-9-example"
    change_dir = tmp_path / "openspec" / "changes" / change
    change_dir.mkdir(parents=True)
    archive = tmp_path / "openspec" / "changes" / "archive"
    archive.mkdir()
    lock = archive / ".openspec-archive.lock"
    tasks = change_dir / "tasks.md"
    tasks.write_text(
        f"- [x] 1.1 done\n- [ ] 7.3 `finish_change.py {change}` archives; the person merges\n",
        encoding="utf-8",
    )
    scripts = tmp_path / ".agent-process" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "request_codex_review.py").write_text("", encoding="utf-8")
    order: list[str] = []
    waited: list[int] = []

    def run(cmd: list[str]) -> str:
        if "archive" in cmd:
            order.append("archive")
            assert "- [x] 7.3" in tasks.read_text(encoding="utf-8")
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
        if cmd[:3] == ["gh", "pr", "view"]:
            return json.dumps({"number": 9})
        if cmd[0] == sys.executable and "--request" in cmd:
            order.append("request-review")
            return ""
        if cmd[:2] == ["git", "add"]:
            return ""
        raise AssertionError(f"unexpected call: {cmd}")

    def wait(pr: int) -> int:
        waited.append(pr)
        order.append("wait")
        return 0

    assert finish_change.finish_change(change, root=tmp_path, run=run, wait=wait) == 0
    assert order == ["archive", "commit", "push", "request-review", "wait"]
    assert waited == [9]

    lock.write_text("", encoding="utf-8")
    order.clear()
    assert finish_change.finish_change(change, root=tmp_path, run=run, wait=wait) == 2
    assert order == []
