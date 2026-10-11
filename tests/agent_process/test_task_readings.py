"""Tests for `.agent-process/scripts/task_readings.py` — one merged PR's readings row.

GitHub and Grafana are in-memory doubles behind the script's protocols; the merged tree is a
`tmp_path` holding an archived change, and the CSV is a file beside it.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.task_readings import COLUMNS, main, query_result

_ISSUE = 7
_TOKEN = f"tracking issue {_ISSUE}"
_LATER_TOKEN = f"tracking issue {_ISSUE + 92}"
_MERGED_AT = "2026-10-10T16:00:00Z"
_MERGED = datetime(2026, 10, 10, 16, tzinfo=UTC).timestamp()
_START = _MERGED - 5400
_HEADER = (
    "pr,change,task_id,attempt_id,start,merged_at,hours,lines,plan_rounds,code_rounds,"
    "cost_usd,api_requests,failed,denied,compactions,unlaunched_events,gap"
)
_ENV = {
    "GITHUB_REPOSITORY": "o/r",
    "GRAFANA_URL": "https://grafana.example",
    "GRAFANA_SERVICE_ACCOUNT_TOKEN": "token",
}


def _comment(login: str, sha: str) -> dict[str, object]:
    return {"author": {"login": login}, "body": f"Reviewed head SHA: {sha}\n\nnotes"}


def _pull(head: str = "demo", comments: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "mergedAt": _MERGED_AT,
        "additions": 90,
        "deletions": 10,
        "headRefName": head,
        "comments": comments
        if comments is not None
        else [_comment("github-actions", "a" * 40), _comment("github-actions", "b" * 40)],
    }


class _GitHub:
    def __init__(self, pull: Mapping[str, object] | Exception) -> None:
        self.pull = pull

    def pull_request(self, pr: int) -> Mapping[str, object]:
        if isinstance(self.pull, Exception):
            raise self.pull
        return self.pull


def _sample(labels: dict[str, str], value: float) -> dict[str, object]:
    return {"metric": labels, "value": [_MERGED, str(value)]}


def _count(task: str, attempt: str, event: str, n: int, **fields: str) -> dict[str, object]:
    return _sample({"task_id": task, "attempt_id": attempt, "event_name": event, **fields}, n)


_COMPACTION = _count("issue-7", "10", "compaction", 1, success="true")
_COUNTS = [
    _count("issue-7", "10", "api_request", 20),
    _count("issue-7", "10", "tool_result", 30, success="true"),
    _count("issue-7", "10", "tool_result", 2, success="false"),
    _count("issue-7", "10", "tool_decision", 31, decision="accept"),
    _count("issue-7", "10", "tool_decision", 1, decision="reject"),
    _COMPACTION,
    _count("issue-7", "9", "api_request", 4),
    _count("issue-8", "1", "api_request", 6),
    _count("", "", "api_request", 3),
    _count("unassigned", "", "tool_result", 2, success="true"),
]


class _Grafana:
    def __init__(
        self,
        starts: dict[str, float] | None = None,
        counts: list[dict[str, object]] | None = None,
        lookback: int = 0,
        error: Exception | None = None,
    ) -> None:
        self.starts = {"9": _START - 86400, "10": _START} if starts is None else starts
        self.counts = _COUNTS if counts is None else counts
        self.lookback = lookback
        self.error = error
        self.calls: list[tuple[str, str, float]] = []

    def prometheus(self, query: str, time: float) -> Sequence[Mapping[str, object]]:
        self.calls.append(("prometheus", query, time))
        if self.error is not None:
            raise self.error
        return [_sample({"attempt_id": k}, v) for k, v in self.starts.items()]

    def loki(self, query: str, time: float) -> Sequence[Mapping[str, object]]:
        self.calls.append(("loki", query, time))
        if "unwrap cost_usd" in query:
            return [_sample({"task_id": "issue-7", "attempt_id": "10"}, 1.2345678)]
        if "[30d]" in query:
            return [_sample({}, self.lookback)] if self.lookback else []
        return self.counts


def _tree(tmp_path: Path, review: dict[str, object] | None = None, name: str = "demo") -> Path:
    change = tmp_path / "openspec" / "changes" / "archive" / f"2026-10-10-{name}"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text(
        f"## 0. Delivery start\n\n- [x] 0.1 Run start_change for {_TOKEN}\n"
        f"- [x] 1.1 A test fixture names {_LATER_TOKEN}\n",
        encoding="utf-8",
    )
    payload = {"verdict": "approve", "round": 2} if review is None else review
    (change / "architect-review.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def _csv_path(tmp_path: Path) -> Path:
    return tmp_path / "readings" / "task-readings.csv"


def _csv(tmp_path: Path, rows: Sequence[str] = ()) -> Path:
    path = _csv_path(tmp_path)
    path.parent.mkdir()
    path.write_bytes(("\n".join([_HEADER, *rows]) + "\n").encode("utf-8"))
    return path


def _run(
    tmp_path: Path,
    github: _GitHub,
    grafana: _Grafana,
    environ: Mapping[str, str] = _ENV,
    pr: int = 12,
) -> int:
    argv = [
        "--pr",
        str(pr),
        "--csv",
        str(_csv_path(tmp_path)),
        "--root",
        str(tmp_path),
    ]
    return main(argv, environ, github, grafana)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _row(path: Path, pr: str = "12") -> dict[str, str]:
    matching = [row for row in _rows(path) if row["pr"] == pr]
    assert len(matching) == 1
    return matching[0]


_TELEMETRY = (
    "attempt_id",
    "start",
    "hours",
    "cost_usd",
    "api_requests",
    "failed",
    "denied",
    "compactions",
    "unlaunched_events",
)


def test_task_pr_merged(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    code = _run(tmp_path, _GitHub(_pull()), _Grafana())

    assert code == 0
    assert path.read_text(encoding="utf-8").splitlines()[0] == _HEADER
    assert ",".join(COLUMNS) == _HEADER
    assert _row(path) == {
        "pr": "12",
        "change": "demo",
        "task_id": "issue-7",
        "attempt_id": "10",
        "start": "2026-10-10T14:30:00Z",
        "merged_at": _MERGED_AT,
        "hours": "1.50",
        "lines": "100",
        "plan_rounds": "2",
        "code_rounds": "2",
        "cost_usd": "1.2346",
        "api_requests": "20",
        "failed": "2",
        "denied": "1",
        "compactions": "1",
        "unlaunched_events": "5",
        "gap": "",
    }


def test_rerun_for_a_recorded_pr(tmp_path: Path) -> None:
    old = "12,demo,issue-7,1,,,,,,,,,,,,,telemetry: old"
    path = _csv(_tree(tmp_path), ["5,a,issue-1,1,,,,,,,,,,,,,", old, "13,b,issue-2,1,,,,,,,,,,,,,"])
    counts = [row for row in _COUNTS if row is not _COMPACTION]
    code = _run(tmp_path, _GitHub(_pull()), _Grafana(counts=counts, lookback=3))

    assert code == 0
    assert [row["pr"] for row in _rows(path)] == ["5", "12", "13"]
    row = _row(path)
    assert row["attempt_id"] == "10"
    assert row["compactions"] == "0"
    assert row["gap"] == ""


def test_release_pr_merged(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    before = path.read_bytes()
    grafana = _Grafana()
    code = _run(tmp_path, _GitHub(_pull(head="release-please--branches--main")), grafana)

    assert code == 0
    assert path.read_bytes() == before
    assert grafana.calls == []


def test_task_without_telemetry(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    grafana = _Grafana(starts={})
    code = _run(tmp_path, _GitHub(_pull()), grafana)

    assert code == 1
    row = _row(path)
    assert all(row[column] == "" for column in _TELEMETRY)
    assert row["gap"] == "telemetry: no token sample of issue-7"
    assert row["lines"] == "100"
    assert [call[0] for call in grafana.calls] == ["prometheus"]


@pytest.mark.parametrize(
    ("environ", "error", "cause"),
    [
        (_ENV, RuntimeError("HTTP 502"), "HTTP 502"),
        ({**_ENV, "GRAFANA_SERVICE_ACCOUNT_TOKEN": ""}, None, "GRAFANA_SERVICE_ACCOUNT_TOKEN"),
    ],
    ids=["http-error", "unset-credential"],
)
def test_grafana_unreachable(
    tmp_path: Path, environ: Mapping[str, str], error: Exception | None, cause: str
) -> None:
    path = _csv(_tree(tmp_path))
    grafana = _Grafana(error=error)
    code = _run(tmp_path, _GitHub(_pull()), grafana, environ=environ)

    assert code == 1
    row = _row(path)
    assert all(row[column] == "" for column in _TELEMETRY)
    assert row["gap"].startswith("telemetry: ")
    assert cause in row["gap"]
    assert row["code_rounds"] == "2"
    if error is None:
        assert grafana.calls == []


def test_absent_field_is_missing_not_zero(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    counts = [
        _count("issue-7", "10", "api_request", 20),
        _count("issue-7", "10", "tool_result", 30, success=""),
        _count("issue-7", "10", "tool_decision", 31, decision="accept"),
    ]
    code = _run(tmp_path, _GitHub(_pull()), _Grafana(counts=counts))

    assert code == 1
    row = _row(path)
    assert row["failed"] == ""
    assert row["compactions"] == ""
    assert row["denied"] == "0"
    assert row["api_requests"] == "20"
    causes = row["gap"].split("; ")
    assert any(cause.startswith("failed: ") for cause in causes)
    assert any(cause.startswith("compactions: ") for cause in causes)


def test_review_without_round_is_gap(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path, review={"verdict": "approve"}))
    code = _run(tmp_path, _GitHub(_pull()), _Grafana())

    assert code == 1
    row = _row(path)
    assert row["plan_rounds"] == ""
    assert row["gap"] == "plan_rounds: review without round"


def test_code_rounds_count_distinct_reviewed_heads(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    comments: list[dict[str, object]] = [
        _comment("github-actions", "a" * 40),
        _comment("github-actions[bot]", "a" * 40),
        _comment("github-actions", "b" * 40),
        _comment("someone", "c" * 40),
        {"author": {"login": "github-actions"}, "body": "a summary without the marker"},
    ]
    code = _run(tmp_path, _GitHub(_pull(comments=comments)), _Grafana())

    assert code == 0
    assert _row(path)["code_rounds"] == "2"


def test_unknown_task_writes_no_row_and_fails(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    before = path.read_bytes()
    grafana = _Grafana()
    code = _run(tmp_path, _GitHub(RuntimeError("gh pr view 12 failed")), grafana)

    assert code != 0
    assert path.read_bytes() == before
    assert grafana.calls == []


def test_archived_change_matched_exactly(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path, name="x-demo"))
    before = path.read_bytes()
    code = _run(tmp_path, _GitHub(_pull(head="demo")), _Grafana())

    assert code == 0
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "payload",
    [[], "oops", {"status": "error"}, {"status": "success", "data": {"result": {}}}],
    ids=["list", "string", "error-status", "result-not-list"],
)
def test_unexpected_grafana_answer_is_a_runtime_error(payload: object) -> None:
    with pytest.raises(RuntimeError, match="unexpected answer"):
        query_result(payload)
