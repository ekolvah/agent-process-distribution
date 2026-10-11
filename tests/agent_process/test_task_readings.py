"""Tests for `.agent-process/scripts/task_readings.py` — one merged PR's readings row.

GitHub and Grafana are in-memory doubles behind the script's protocols; the merged tree is a
`tmp_path` holding an archived change, and the CSV is a file beside it.
"""

from __future__ import annotations

import csv
import json
import re
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
    "pr,change,task_id,start,merged_at,hours,lines,plan_rounds,code_rounds,"
    "cost_usd,api_requests,failed,denied,compactions,gap"
)
_EARLIER_HEADER = (
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


# One session's events of one shape: (session_id, event_name, count, fields).
_Event = tuple[str, str, int, dict[str, str]]


def _event(session: str, event: str, n: int, **fields: str) -> _Event:
    return session, event, n, fields


_COMPACTION = _event("s-a", "compaction", 1, success="true")
_EVENTS = [
    _event("s-a", "api_request", 12),
    _event("s-b", "api_request", 8),
    _event("s-a", "tool_result", 30, success="true"),
    _event("s-b", "tool_result", 2, success="false"),
    _event("s-a", "tool_decision", 31, decision="accept"),
    _event("s-b", "tool_decision", 1, decision="reject"),
    _COMPACTION,
]
# A parallel session of another task, inside the window.
_PARALLEL = [_event("s-x", "api_request", 6), _event("s-x", "tool_result", 4, success="false")]
_COST_PER_REQUEST = 0.0625


class _Grafana:
    """Answers from per-session data, keeping only the sessions the query's
    `session_id=~"…"` matcher names and grouping by `event_name` and its fields."""

    def __init__(
        self,
        starts: dict[str, float] | None = None,
        events: list[_Event] | None = None,
        lookback: int = 0,
        error: Exception | None = None,
    ) -> None:
        self.starts = {"s-a": _START, "s-b": _START + 600} if starts is None else starts
        self.events = _EVENTS + _PARALLEL if events is None else events
        self.lookback = lookback
        self.error = error
        self.calls: list[tuple[str, str, float]] = []

    @staticmethod
    def _matches(query: str, session: str) -> bool:
        matcher = re.search(r'session_id=~"([^"]*)"', query)
        return matcher is not None and re.fullmatch(matcher.group(1), session) is not None

    def prometheus(self, query: str, time: float) -> Sequence[Mapping[str, object]]:
        self.calls.append(("prometheus", query, time))
        if self.error is not None:
            raise self.error
        return [
            _sample({"session_id": s}, v) for s, v in self.starts.items() if self._matches(query, s)
        ]

    def loki(self, query: str, time: float) -> Sequence[Mapping[str, object]]:
        self.calls.append(("loki", query, time))
        if "[30d]" in query:
            return [_sample({}, self.lookback)] if self.lookback else []
        mine = [e for e in self.events if self._matches(query, e[0])]
        if "unwrap cost_usd" in query:
            cost = sum(n * _COST_PER_REQUEST for _, event, n, _ in mine if event == "api_request")
            return [_sample({}, cost)] if cost else []
        groups: dict[tuple[tuple[str, str], ...], int] = {}
        for _, event, n, fields in mine:
            key = tuple(sorted({"event_name": event, **fields}.items()))
            groups[key] = groups.get(key, 0) + n
        return [_sample(dict(key), n) for key, n in groups.items()]


def _tree(
    tmp_path: Path,
    review: dict[str, object] | None = None,
    name: str = "demo",
    sessions: str | None = "s-a\ns-b\n",
) -> Path:
    change = tmp_path / "openspec" / "changes" / "archive" / f"2026-10-10-{name}"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text(
        f"## 0. Delivery start\n\n- [x] 0.1 Run start_change for {_TOKEN}\n"
        f"- [x] 1.1 A test fixture names {_LATER_TOKEN}\n",
        encoding="utf-8",
    )
    payload = {"verdict": "approve", "round": 2} if review is None else review
    (change / "architect-review.json").write_text(json.dumps(payload), encoding="utf-8")
    if sessions is not None:
        (change / "sessions").write_text(sessions, encoding="utf-8")
    return tmp_path


def _csv_path(tmp_path: Path) -> Path:
    return tmp_path / "readings" / "task-readings.csv"


def _csv(tmp_path: Path, rows: Sequence[str] = (), header: str = _HEADER) -> Path:
    path = _csv_path(tmp_path)
    path.parent.mkdir()
    path.write_bytes(("\n".join([header, *rows]) + "\n").encode("utf-8"))
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
    "start",
    "hours",
    "cost_usd",
    "api_requests",
    "failed",
    "denied",
    "compactions",
)


def test_task_pr_merged(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    grafana = _Grafana()
    code = _run(tmp_path, _GitHub(_pull()), grafana)

    assert code == 0
    assert path.read_text(encoding="utf-8").splitlines()[0] == _HEADER
    assert ",".join(COLUMNS) == _HEADER
    assert _row(path) == {
        "pr": "12",
        "change": "demo",
        "task_id": "issue-7",
        "start": "2026-10-10T14:30:00Z",
        "merged_at": _MERGED_AT,
        "hours": "1.50",
        "lines": "100",
        "plan_rounds": "2",
        "code_rounds": "2",
        "cost_usd": "1.2500",
        "api_requests": "20",
        "failed": "2",
        "denied": "1",
        "compactions": "1",
        "gap": "",
    }
    queries = [query for kind, query, _ in grafana.calls if kind in ("prometheus", "loki")]
    assert all('session_id=~"s-a|s-b"' in q for q in queries if "[30d]" not in q)
    assert not any("task_id" in q for q in queries)


def test_rerun_for_a_recorded_pr(tmp_path: Path) -> None:
    old = "12,demo,issue-7,,,,,,,,,,,,telemetry: old"
    path = _csv(_tree(tmp_path), ["5,a,issue-1,,,,,,,,,,,,", old, "13,b,issue-2,,,,,,,,,,,,"])
    events = [e for e in _EVENTS if e is not _COMPACTION]
    code = _run(tmp_path, _GitHub(_pull()), _Grafana(events=events, lookback=3))

    assert code == 0
    assert [row["pr"] for row in _rows(path)] == ["5", "12", "13"]
    row = _row(path)
    assert row["api_requests"] == "20"
    assert row["compactions"] == "0"
    assert row["gap"] == ""


def test_file_with_an_earlier_header(tmp_path: Path) -> None:
    earlier = "5,a,issue-1,2,,,,,,,0.5000,,,,,3,"
    path = _csv(_tree(tmp_path), [earlier], header=_EARLIER_HEADER)
    code = _run(tmp_path, _GitHub(_pull()), _Grafana())

    assert code == 0
    assert path.read_text(encoding="utf-8").splitlines()[0] == _HEADER
    kept = _row(path, "5")
    assert (kept["pr"], kept["task_id"], kept["cost_usd"]) == ("5", "issue-1", "0.5000")
    assert _row(path)["cost_usd"] == "1.2500"


def test_release_pr_merged(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    before = path.read_bytes()
    grafana = _Grafana()
    code = _run(tmp_path, _GitHub(_pull(head="release-please--branches--main")), grafana)

    assert code == 0
    assert path.read_bytes() == before
    assert grafana.calls == []


@pytest.mark.parametrize("sessions", [None, "", "\n"], ids=["absent", "empty", "blank"])
def test_task_without_telemetry(tmp_path: Path, sessions: str | None) -> None:
    path = _csv(_tree(tmp_path, sessions=sessions))
    grafana = _Grafana()
    code = _run(tmp_path, _GitHub(_pull()), grafana)

    assert code == 1
    row = _row(path)
    assert all(row[column] == "" for column in _TELEMETRY)
    assert row["gap"] == "telemetry: no bound session"
    assert row["lines"] == "100"
    assert grafana.calls == []


def test_bound_session_without_telemetry(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    events = [e for e in _EVENTS if e[0] == "s-a"]
    code = _run(tmp_path, _GitHub(_pull()), _Grafana(starts={"s-a": _START}, events=events))

    assert code == 1
    row = _row(path)
    assert row["start"] == "2026-10-10T14:30:00Z"
    assert row["api_requests"] == "12"
    assert row["cost_usd"] == "0.7500"
    assert row["gap"] == "telemetry: no token sample of s-b"


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


def test_parallel_session_of_another_task(tmp_path: Path) -> None:
    alone = _csv(_tree(tmp_path / "alone"))
    _run(tmp_path / "alone", _GitHub(_pull()), _Grafana(events=_EVENTS))
    beside = _csv(_tree(tmp_path / "beside"))
    _run(tmp_path / "beside", _GitHub(_pull()), _Grafana(events=_EVENTS + _PARALLEL))

    for column in ("cost_usd", "api_requests", "failed"):
        assert _row(beside)[column] == _row(alone)[column] != ""


def test_absent_field_is_missing_not_zero(tmp_path: Path) -> None:
    path = _csv(_tree(tmp_path))
    events = [
        _event("s-a", "api_request", 20),
        _event("s-a", "tool_result", 30, success=""),
        _event("s-a", "tool_decision", 31, decision="accept"),
    ]
    code = _run(tmp_path, _GitHub(_pull()), _Grafana(events=events))

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
