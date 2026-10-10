"""Tests for `.agent-process/scripts/task_metrics.py` — one task's delivery reading.

Grafana and GitHub are in-memory doubles behind the script's two protocols; the real
adapters are checked once, live, by the change's baseline reading.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from scripts.task_metrics import PullRequest, main, reading, start_query

_ISSUE = 101
_START = 1791644556.698  # 2026-10-10T15:02:36.698Z, the observed first sample of issue-101
_MERGED = datetime(2026, 10, 10, 16, 19, 44, tzinfo=UTC)
_COMMIT = "5de04c93"
_BRANCH = "one-emitter-task-telemetry"
_ARCHIVE = "openspec/changes/archive"
_ENTRY = f"2026-10-10-{_BRANCH}"
_ENV = {"GRAFANA_URL": "https://grafana.example", "GRAFANA_SERVICE_ACCOUNT_TOKEN": "t"}
_KEYS = {
    "task_id",
    "attempt_id",
    "pr",
    "start",
    "merged",
    "hours_to_merge",
    "lines_changed",
    "plan_rounds",
    "code_rounds",
    "gaps",
}


def _pr(number: int = 382, merged_at: datetime | None = _MERGED, **fields: object) -> PullRequest:
    values: dict[str, object] = {
        "number": number,
        "merged_at": merged_at,
        "merge_commit": _COMMIT if merged_at else None,
        "head_branch": _BRANCH,
        "additions": 922,
        "deletions": 76,
    }
    values.update(fields)
    return PullRequest(**values)  # type: ignore[arg-type]


def _reviewed(sha: str) -> tuple[str, str]:
    return ("github-actions", f"Reviewed head SHA: {sha}\n\nP2 finding")


class _Prometheus:
    def __init__(self, value: float | None = _START) -> None:
        self.value = value
        self.queries: list[str] = []

    def instant(self, expr: str) -> float | None:
        self.queries.append(expr)
        return self.value


class _GitHub:
    def __init__(
        self,
        prs: list[PullRequest] | None = None,
        comments: list[tuple[str, str]] | None = None,
        review: dict[str, object] | None = None,
    ) -> None:
        self.prs = [_pr()] if prs is None else prs
        self.comment_list = (
            [_reviewed("a1"), _reviewed("b2"), _reviewed("c3")] if comments is None else comments
        )
        self.review = {"verdict": "approve", "round": 2} if review is None else review
        self.calls: list[str] = []

    def connected_prs(self, issue: int) -> list[PullRequest]:
        self.calls.append(f"prs {issue}")
        return self.prs

    def comments(self, pr: int) -> list[tuple[str, str]]:
        self.calls.append(f"comments {pr}")
        return self.comment_list

    def tree(self, commit: str, path: str) -> list[str] | None:
        self.calls.append(f"tree {commit}:{path}")
        if (commit, path) == (_COMMIT, _ARCHIVE):
            return ["2026-10-09-other-change", _ENTRY]
        return None

    def blob(self, commit: str, path: str) -> str | None:
        self.calls.append(f"blob {commit}:{path}")
        if (commit, path) == (_COMMIT, f"{_ARCHIVE}/{_ENTRY}/architect-review.json"):
            return json.dumps(self.review)
        return None


def _run(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    *,
    prometheus: _Prometheus | None = None,
    github: _GitHub | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    prom = prometheus or _Prometheus()
    try:
        code = main(
            argv,
            _ENV if environ is None else environ,
            prometheus=lambda url, token: prom,
            github=github or _GitHub(),
        )
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    out, err = capsys.readouterr()
    return code, out, err


class TestStart:
    def test_query_matches_the_task_exactly(self) -> None:
        expr = start_query(101, 1)
        assert 'task_id="issue-101"' in expr and 'attempt_id="1"' in expr
        assert "=~" not in expr and "!=" not in expr
        prometheus = _Prometheus()
        result = reading(101, 1, prometheus, _GitHub())
        assert prometheus.queries == [expr]
        assert result["start"] == "2026-10-10T15:02:36Z"
        assert result["hours_to_merge"] == 1.29

    def test_no_sample_is_the_start_gap(self) -> None:
        result = reading(101, 1, _Prometheus(None), _GitHub())
        assert result["start"] is None and result["hours_to_merge"] is None
        assert "start: no token sample of issue-101 attempt 1" in result["gaps"]  # type: ignore[operator]


class TestPullRequest:
    def test_merged_after_the_start_is_the_task_pr(self) -> None:
        before = _pr(number=104, merged_at=datetime(2026, 10, 1, tzinfo=UTC))
        unmerged = _pr(number=390, merged_at=None)
        result = reading(101, 1, _Prometheus(), _GitHub(prs=[before, _pr(), unmerged]))
        assert result["pr"] == 382
        assert result["merged"] == "2026-10-10T16:19:44Z"

    def test_none_is_the_merge_gap(self) -> None:
        github = _GitHub(prs=[_pr(number=390, merged_at=None)])
        result = reading(101, 1, _Prometheus(), github)
        assert result["pr"] is None and result["merged"] is None
        assert result["lines_changed"] is None and result["code_rounds"] is None
        assert f"merge: no merged PR connected to issue {_ISSUE}" in result["gaps"]  # type: ignore[operator]
        assert github.calls == [f"prs {_ISSUE}"]

    def test_two_exit_2_naming_both(self, capsys: pytest.CaptureFixture[str]) -> None:
        github = _GitHub(prs=[_pr(), _pr(number=385)])
        code, out, err = _run(["--issue", "101"], capsys, github=github)
        assert code == 2 and out == ""
        assert "382" in err and "385" in err


class TestSize:
    def test_lines_changed_is_additions_plus_deletions(self) -> None:
        assert reading(101, 1, _Prometheus(), _GitHub())["lines_changed"] == 998


class TestRounds:
    def test_code_rounds_count_distinct_reviewed_heads(self) -> None:
        comments = [
            _reviewed("a1"),
            _reviewed("a1"),
            _reviewed("b2"),
            ("someone", "Reviewed head SHA: c3"),
            ("github-actions", "Release notes\nReviewed head SHA: d4"),
        ]
        result = reading(101, 1, _Prometheus(), _GitHub(comments=comments))
        assert result["code_rounds"] == 2

    def test_plan_rounds_are_the_archived_round(self) -> None:
        github = _GitHub()
        assert reading(101, 1, _Prometheus(), github)["plan_rounds"] == 2
        assert f"blob {_COMMIT}:{_ARCHIVE}/{_ENTRY}/architect-review.json" in github.calls

    def test_review_without_round_is_a_gap(self) -> None:
        result = reading(101, 1, _Prometheus(), _GitHub(review={"verdict": "approve"}))
        assert result["plan_rounds"] is None
        gaps = result["gaps"]
        assert isinstance(gaps, list) and any(g.startswith("plan rounds:") for g in gaps)

    def test_no_archived_change_is_a_gap(self) -> None:
        result = reading(
            101, 1, _Prometheus(), _GitHub(prs=[_pr(head_branch="emitter-task-telemetry")])
        )
        assert result["plan_rounds"] is None
        gaps = result["gaps"]
        assert isinstance(gaps, list) and any(g.startswith("plan rounds:") for g in gaps)


class TestArguments:
    @pytest.mark.parametrize("missing", ["GRAFANA_URL", "GRAFANA_SERVICE_ACCOUNT_TOKEN"])
    def test_missing_credential_exits_2_naming_it(
        self, missing: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        environ = {k: v for k, v in _ENV.items() if k != missing}
        prometheus, github = _Prometheus(), _GitHub()
        code, out, err = _run(
            ["--issue", "101"], capsys, prometheus=prometheus, github=github, environ=environ
        )
        assert code == 2 and out == ""
        assert missing in err
        assert prometheus.queries == [] and github.calls == []

    @pytest.mark.parametrize(
        "argv", [["--issue", "x"], ["--issue", "0"], [], ["--issue", "1", "--attempt", "-1"]]
    )
    def test_bad_arguments_exit_2(
        self, argv: list[str], capsys: pytest.CaptureFixture[str]
    ) -> None:
        github = _GitHub()
        code, _, _ = _run(argv, capsys, github=github)
        assert code == 2 and github.calls == []


class TestExit:
    def test_no_gap_exits_0(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = _run(["--issue", "101", "--attempt", "1"], capsys)
        assert code == 0
        printed = json.loads(out)
        assert set(printed) == _KEYS
        assert printed["task_id"] == "issue-101" and printed["attempt_id"] == "1"
        assert printed["gaps"] == []

    def test_a_gap_exits_1(self, capsys: pytest.CaptureFixture[str]) -> None:
        code, out, _ = _run(["--issue", "101"], capsys, prometheus=_Prometheus(None))
        assert code == 1
        assert json.loads(out)["gaps"] == ["start: no token sample of issue-101 attempt 1"]

    def test_failed_read_exits_2(self, capsys: pytest.CaptureFixture[str]) -> None:
        class _Down(_GitHub):
            def connected_prs(self, issue: int) -> list[PullRequest]:
                raise RuntimeError("gh api graphql failed: HTTP 502")

        code, out, err = _run(["--issue", "101"], capsys, github=_Down())
        assert code == 2 and out == ""
        assert "HTTP 502" in err
