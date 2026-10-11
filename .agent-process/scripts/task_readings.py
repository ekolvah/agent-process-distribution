#!/usr/bin/env python3
"""Record one merged task PR's readings as a row of `task-readings.csv`.

The task is the change archived on `main` under the PR's head branch. Its key is
`task_id=issue-<N>` from the change's tracking token and the highest `attempt_id` the launcher
put on the task's token samples. A reading that cannot be taken leaves its cell empty and names
its cause in `gap`, never a 0; a row with a gap exits 1, so the run shows red. A PR that is not
a task leaves the file alone and exits 0. Without the task there is no key, so a failure before
it is known writes nothing and exits 2.

The GitHub reads are the documented ones of the telemetry setup document, "Per-task readings",
and the telemetry reads its "Per-task metrics" queries, over the task's own window.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

try:
    from scripts.gh_io import run_gh
    from scripts.head_review import _REVIEWED_HEAD, _by_reviewer
except ModuleNotFoundError:  # run as a script from `.agent-process/`
    from gh_io import run_gh  # type: ignore[import-not-found, no-redef]
    from head_review import (  # type: ignore[import-not-found, no-redef]
        _REVIEWED_HEAD,
        _by_reviewer,
    )

COLUMNS = (
    "pr",
    "change",
    "task_id",
    "attempt_id",
    "start",
    "merged_at",
    "hours",
    "lines",
    "plan_rounds",
    "code_rounds",
    "cost_usd",
    "api_requests",
    "failed",
    "denied",
    "compactions",
    "unlaunched_events",
    "gap",
)
CREDENTIALS = ("GRAFANA_URL", "GRAFANA_SERVICE_ACCOUNT_TOKEN")
ARCHIVE = Path("openspec") / "changes" / "archive"
# start_change's token pattern, copied: the hyphenated `skills/agent-process` path is not a package.
_TOKEN = re.compile(r"tracking issue (<N>|\d+)")
_LAUNCHED = re.compile(r"issue-[0-9]+")
_START_QUERY = (
    "min by (attempt_id) (min_over_time(timestamp(claude_code_token_usage_tokens_total"
    '{{task_id="{task}",vcs_repository_name="{repo}"}})[30d:1m]))'
)
_SELECTOR = '{{service_name="claude-code"}} | vcs_repository_name="{repo}"'
_COST_QUERY = (
    "sum by (task_id, attempt_id) (sum_over_time({selector}"
    ' | task_id="{task}" | attempt_id="{attempt}" | event_name="api_request"'
    " | unwrap cost_usd [{window}s]))"
)
_COUNTS_QUERY = (
    "sum by (task_id, attempt_id, event_name, success, decision) (count_over_time({selector}"
    ' | event_name=~"api_request|tool_result|tool_decision|compaction" [{window}s]))'
)
_COMPACTION_LOOKBACK = 'sum(count_over_time({selector} | event_name="compaction" [30d]))'


class GitHub(Protocol):
    def pull_request(self, pr: int) -> Mapping[str, object]: ...


class Grafana(Protocol):
    def prometheus(self, query: str, time: float) -> Sequence[Mapping[str, object]]: ...

    def loki(self, query: str, time: float) -> Sequence[Mapping[str, object]]: ...


Cells = tuple[dict[str, str], list[str]]


def _archived_change(root: Path, change: str) -> Path | None:
    """The directory named exactly `YYYY-MM-DD-<change>`, the latest if archived twice."""
    archive = root / ARCHIVE
    if not change or not archive.is_dir():
        return None
    pattern = re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(change)}")
    found = sorted(p for p in archive.iterdir() if p.is_dir() and pattern.fullmatch(p.name))
    return found[-1] if found else None


def _issue(tasks_md: Path) -> int:
    match = _TOKEN.search(tasks_md.read_text(encoding="utf-8"))
    if match is None or match.group(1) == "<N>":
        raise RuntimeError(f"{tasks_md}: no numbered tracking issue token")
    return int(match.group(1))


def _merged(pull: Mapping[str, object], pr: int) -> float:
    merged_at = pull.get("mergedAt")
    if not isinstance(merged_at, str) or not merged_at:
        raise RuntimeError(f"PR {pr} is not merged")
    return datetime.fromisoformat(merged_at).timestamp()


def _github_cells(pull: Mapping[str, object]) -> Cells:
    cells: dict[str, str] = {}
    gaps: list[str] = []
    additions, deletions = pull.get("additions"), pull.get("deletions")
    if isinstance(additions, int) and isinstance(deletions, int):
        cells["lines"] = str(additions + deletions)
    else:
        gaps.append("lines: no additions or deletions")
    comments = pull.get("comments")
    heads = {
        match.group("sha")
        for comment in (comments if isinstance(comments, list) else [])
        if isinstance(comment, Mapping)
        and _by_reviewer(comment)
        and (match := _REVIEWED_HEAD.search(str(comment.get("body") or ""))) is not None
    }
    if heads:
        cells["code_rounds"] = str(len(heads))
    else:
        gaps.append("code_rounds: no reviewed head")
    return cells, gaps


def _plan_rounds(change_dir: Path) -> Cells:
    path = change_dir / "architect-review.json"
    try:
        review = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, ["plan_rounds: no architect-review.json"]
    except (OSError, ValueError) as exc:
        return {}, [f"plan_rounds: unreadable review ({exc})"]
    rounds = review.get("round") if isinstance(review, dict) else None
    if not isinstance(rounds, int) or isinstance(rounds, bool):
        return {}, ["plan_rounds: review without round"]
    return {"plan_rounds": str(rounds)}, []


def _labels(sample: Mapping[str, object]) -> Mapping[str, object]:
    metric = sample.get("metric")
    return metric if isinstance(metric, Mapping) else {}


def _value(sample: Mapping[str, object]) -> float:
    value = sample.get("value")
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"unexpected sample shape: {sample!r}")
    return float(value[1])


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_cells(rows: Sequence[Mapping[str, object]], task: str, attempt: int) -> Cells:
    """The task's counts, each 0 only where its field is shown to exist; and rule 1."""
    mine = [
        (_labels(row), _value(row))
        for row in rows
        if _labels(row).get("task_id") == task and _labels(row).get("attempt_id") == str(attempt)
    ]

    def total(event: str, field: str = "", value: str | None = None) -> int | None:
        found = [(labels, n) for labels, n in mine if labels.get("event_name") == event]
        if field:
            found = [(labels, n) for labels, n in found if labels.get(field)]
        if not found:
            return None
        return int(sum(n for labels, n in found if value is None or labels.get(field) == value))

    readings = {
        "api_requests": (total("api_request"), "no api_request event"),
        "failed": (total("tool_result", "success", "false"), "no tool_result with success"),
        "denied": (total("tool_decision", "decision", "reject"), "no tool_decision with decision"),
        "compactions": (total("compaction"), ""),
    }
    cells = {name: str(n) for name, (n, _) in readings.items() if n is not None}
    gaps = [f"{name}: {cause}" for name, (n, cause) in readings.items() if n is None and cause]
    unlaunched = sum(
        _value(row) for row in rows if not _LAUNCHED.fullmatch(str(_labels(row).get("task_id", "")))
    )
    cells["unlaunched_events"] = str(int(unlaunched))
    return cells, gaps


def _telemetry(grafana: Grafana, repo: str, task: str, merged: float) -> Cells:
    starts: dict[int, float] = {}
    for sample in grafana.prometheus(_START_QUERY.format(task=task, repo=repo), merged):
        attempt_label = str(_labels(sample).get("attempt_id", ""))
        if attempt_label.isdigit():
            starts[int(attempt_label)] = _value(sample)
    if not starts:
        return {}, [f"telemetry: no token sample of {task}"]
    attempt = max(starts)
    start = starts[attempt]
    window = max(1, math.ceil(merged - start))
    selector = _SELECTOR.format(repo=repo)
    cost = grafana.loki(
        _COST_QUERY.format(selector=selector, task=task, attempt=attempt, window=window), merged
    )
    counts = grafana.loki(_COUNTS_QUERY.format(selector=selector, window=window), merged)
    cells = {
        "attempt_id": str(attempt),
        "start": _iso(start),
        "hours": f"{(merged - start) / 3600:.2f}",
    }
    gaps: list[str] = []
    if cost:
        cells["cost_usd"] = f"{sum(_value(sample) for sample in cost):.4f}"
    else:
        gaps.append(f"cost_usd: no api_request cost of {task} attempt {attempt}")
    count_cells, count_gaps = _count_cells(counts, task, attempt)
    cells.update(count_cells)
    gaps.extend(count_gaps)
    if "compactions" not in cells:
        lookback = grafana.loki(_COMPACTION_LOOKBACK.format(selector=selector), merged)
        if sum(_value(sample) for sample in lookback) > 0:
            cells["compactions"] = "0"
        else:
            gaps.append(f"compactions: no compaction row of {repo} in retention")
    return cells, gaps


def _telemetry_or_gap(
    environ: Mapping[str, str], grafana: Grafana, repo: str, task: str, merged: float
) -> Cells:
    unset = [name for name in CREDENTIALS if not environ.get(name)]
    if unset:
        return {}, [f"telemetry: unset {', '.join(unset)}"]
    try:
        return _telemetry(grafana, repo, task, merged)
    except (OSError, RuntimeError, ValueError) as exc:
        return {}, [f"telemetry: Grafana query failed: {' '.join(str(exc).split())}"]


def upsert(path: Path, row: Mapping[str, str]) -> None:
    """Replace the row with the same `pr`, or append it; the other rows keep their order."""
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise RuntimeError(f"{path}: header is not {','.join(COLUMNS)}")
    rows = list(reader)
    if any(old["pr"] == row["pr"] for old in rows):
        rows = [dict(row) if old["pr"] == row["pr"] else old for old in rows]
    else:
        rows.append(dict(row))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_bytes(out.getvalue().encode("utf-8"))


def _parse_options(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pr", type=int, required=True, help="the merged PR number")
    parser.add_argument("--csv", type=Path, required=True, help="task-readings.csv to upsert")
    parser.add_argument("--root", type=Path, default=Path(), help="the merged tree (default .)")
    return parser.parse_args(argv)


def main(argv: Sequence[str], environ: Mapping[str, str], github: GitHub, grafana: Grafana) -> int:
    options = _parse_options(argv)
    repo = environ.get("GITHUB_REPOSITORY", "")
    try:
        if not repo:
            raise RuntimeError("GITHUB_REPOSITORY is unset")
        pull = github.pull_request(options.pr)
        change = str(pull.get("headRefName") or "")
        change_dir = _archived_change(options.root, change)
        if change_dir is None:
            print(f"PR {options.pr}: head {change!r} names no archived change, not a task")
            return 0
        task = f"issue-{_issue(change_dir / 'tasks.md')}"
        merged = _merged(pull, options.pr)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    row = {
        "pr": str(options.pr),
        "change": change,
        "task_id": task,
        "merged_at": str(pull["mergedAt"]),
    }
    gaps: list[str] = []
    for cells, cell_gaps in (
        _plan_rounds(change_dir),
        _github_cells(pull),
        _telemetry_or_gap(environ, grafana, repo, task, merged),
    ):
        row.update(cells)
        gaps.extend(cell_gaps)
    row["gap"] = "; ".join(gaps)
    try:
        upsert(options.csv, row)
    except (RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"PR {options.pr}: {task} recorded" + (f" with gap: {row['gap']}" if gaps else ""))
    return 1 if gaps else 0


def query_result(payload: object) -> Sequence[Mapping[str, object]]:
    """The `data.result` list of a Prometheus or Loki query answer."""
    if isinstance(payload, dict) and payload.get("status") == "success":
        data = payload.get("data")
        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, list):
            return result
    raise RuntimeError(f"unexpected answer: {str(payload)[:200]}")


class _GhGitHub:
    def __init__(self, repo: str) -> None:
        self.repo = repo

    def pull_request(self, pr: int) -> Mapping[str, object]:
        fields = "mergedAt,additions,deletions,headRefName,comments"
        raw = run_gh(["pr", "view", str(pr), "--repo", self.repo, "--json", fields])
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh pr view {pr} returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"gh pr view {pr} returned {type(payload).__name__}")
        return payload


class _HttpGrafana:
    """The datasource proxy: Prometheus answers POST, Loki only GET."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token

    def _result(self, request: urllib.request.Request) -> Sequence[Mapping[str, object]]:
        request.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(request, timeout=60) as response:
            return query_result(json.load(response))

    def prometheus(self, query: str, time: float) -> Sequence[Mapping[str, object]]:
        body = urllib.parse.urlencode({"query": query, "time": f"{time:.3f}"}).encode()
        url = f"{self.url}/api/datasources/proxy/uid/grafanacloud-prom/api/v1/query"
        return self._result(urllib.request.Request(url, data=body, method="POST"))

    def loki(self, query: str, time: float) -> Sequence[Mapping[str, object]]:
        params = urllib.parse.urlencode({"query": query, "time": f"{time:.3f}"})
        url = f"{self.url}/api/datasources/proxy/uid/grafanacloud-logs/loki/api/v1/query?{params}"
        return self._result(urllib.request.Request(url, method="GET"))


if __name__ == "__main__":
    sys.exit(
        main(
            sys.argv[1:],
            os.environ,
            _GhGitHub(os.environ.get("GITHUB_REPOSITORY", "")),
            _HttpGrafana(
                os.environ.get("GRAFANA_URL", ""),
                os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN", ""),
            ),
        )
    )
