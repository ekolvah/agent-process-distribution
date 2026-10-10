"""Read one task's delivery metrics: start to merge beside the size, and review rounds.

    python .agent-process/scripts/task_metrics.py --issue N [--attempt K]

The task is the ADR 0037 identity `task_id=issue-<N>`, `attempt_id=<K>`. Its start is the
first token sample in Grafana with exactly those labels; its PR is the merged PR connected to
the issue; code rounds are the distinct heads the review job reported; plan rounds are the
`round` of the archived architect review. One JSON object is printed. A value that cannot be
read is null and named in `gaps`: exit 1. Exit 2 on bad arguments, a missing credential, an
ambiguous PR or a failed read. Owner-side tooling, next to `task_session.py`; not distributed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

try:
    from scripts.gh_io import run_gh
except ModuleNotFoundError:  # documented direct script entry point
    from gh_io import run_gh  # type: ignore[import-not-found, no-redef]

_CREDENTIALS = ("GRAFANA_URL", "GRAFANA_SERVICE_ACCOUNT_TOKEN")
_DATASOURCE = "grafanacloud-prom"
_ARCHIVE = "openspec/changes/archive"
_REVIEWER = "github-actions"
_REVIEWED = re.compile(r"Reviewed head SHA: ([0-9a-f]+)")


class Prometheus(Protocol):
    def instant(self, expr: str) -> float | None:
        """The scalar of an instant query, or None when its result is empty."""


@dataclass(frozen=True)
class PullRequest:
    number: int
    merged_at: datetime | None
    merge_commit: str | None
    head_branch: str
    additions: int
    deletions: int


class GitHub(Protocol):
    def connected_prs(self, issue: int) -> list[PullRequest]:
        """The PRs of the issue's `ConnectedEvent`s."""

    def comments(self, pr: int) -> list[tuple[str, str]]:
        """Author login and body of each comment on the PR."""

    def tree(self, commit: str, path: str) -> list[str] | None:
        """Entry names of the directory at the commit, or None when it does not exist."""

    def blob(self, commit: str, path: str) -> str | None:
        """Text of the file at the commit, or None when it does not exist."""


class Unreadable(Exception):
    """A reading that cannot be taken: exit 2 naming the cause."""


def start_query(issue: int, attempt: int) -> str:
    """The earliest token sample of the task; the range outlasts retention (design D1)."""
    series = (
        f'claude_code_token_usage_tokens_total{{task_id="issue-{issue}",attempt_id="{attempt}"}}'
    )
    return f"min(min_over_time(timestamp({series})[30d:1m]))"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _task_pr(issue: int, start: datetime | None, prs: list[PullRequest]) -> PullRequest | None:
    """The merged connected PR, merged at or after the start when there is one (design D2)."""
    merged = {
        pr.number: pr
        for pr in prs
        if pr.merged_at is not None and (start is None or pr.merged_at >= start)
    }
    if len(merged) > 1:
        numbers = ", ".join(str(n) for n in sorted(merged))
        raise Unreadable(f"more than one merged PR connected to issue {issue}: {numbers}")
    return next(iter(merged.values()), None)


def _code_rounds(comments: list[tuple[str, str]]) -> int:
    """Distinct heads on the first line of the review job's comments (design D4)."""
    heads = set()
    for author, body in comments:
        found = _REVIEWED.fullmatch(body.split("\n", 1)[0].strip())
        if author == _REVIEWER and found:
            heads.add(found.group(1))
    return len(heads)


def _plan_rounds(pr: PullRequest, github: GitHub) -> tuple[int | None, str | None]:
    """The archived review's `round` at the merge commit, or the gap (design D5)."""
    assert pr.merge_commit is not None
    entry = re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}-{re.escape(pr.head_branch)}")
    names = [n for n in github.tree(pr.merge_commit, _ARCHIVE) or [] if entry.fullmatch(n)]
    if len(names) != 1:
        return None, f"plan rounds: no archived change {pr.head_branch} at {pr.merge_commit}"
    path = f"{_ARCHIVE}/{names[0]}/architect-review.json"
    text = github.blob(pr.merge_commit, path)
    if text is None:
        return None, f"plan rounds: no {path} at {pr.merge_commit}"
    try:
        review = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Unreadable(f"{path} at {pr.merge_commit} is not JSON: {exc}") from exc
    found = review.get("round") if isinstance(review, dict) else None
    if not isinstance(found, int):
        return None, f"plan rounds: {path} has no round"
    return found, None


def reading(issue: int, attempt: int, prometheus: Prometheus, github: GitHub) -> dict[str, object]:
    """One task's reading; every value it could not read is null and named in `gaps`."""
    gaps: list[str] = []
    sample = prometheus.instant(start_query(issue, attempt))
    start = None if sample is None else datetime.fromtimestamp(int(sample), UTC)
    if start is None:
        gaps.append(f"start: no token sample of issue-{issue} attempt {attempt}")
    result: dict[str, object] = {
        "task_id": f"issue-{issue}",
        "attempt_id": str(attempt),
        "pr": None,
        "start": None if start is None else _iso(start),
        "merged": None,
        "hours_to_merge": None,
        "lines_changed": None,
        "plan_rounds": None,
        "code_rounds": None,
        "gaps": gaps,
    }
    pr = _task_pr(issue, start, github.connected_prs(issue))
    if pr is None or pr.merged_at is None:
        gaps.append(f"merge: no merged PR connected to issue {issue}")
        return result
    result["pr"] = pr.number
    result["merged"] = _iso(pr.merged_at)
    if start is not None:
        result["hours_to_merge"] = round((pr.merged_at - start).total_seconds() / 3600, 2)
    result["lines_changed"] = pr.additions + pr.deletions
    rounds = _code_rounds(github.comments(pr.number))
    if rounds:
        result["code_rounds"] = rounds
    else:
        gaps.append(f"code rounds: no reviewed head on the PR {pr.number}")
    result["plan_rounds"], gap = _plan_rounds(pr, github)
    if gap:
        gaps.append(gap)
    return result


class GrafanaProxy:
    """Instant queries through the Grafana datasource proxy, evaluated at the read time."""

    def __init__(self, url: str, token: str) -> None:
        self._endpoint = f"{url.rstrip('/')}/api/datasources/proxy/uid/{_DATASOURCE}/api/v1/query"
        self._token = token

    def instant(self, expr: str) -> float | None:
        request = urllib.request.Request(
            self._endpoint,
            data=urllib.parse.urlencode({"query": expr}).encode("utf-8"),
            headers={"Authorization": f"Bearer {self._token}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Grafana query failed: {exc}") from exc
        if payload.get("status") != "success":
            raise RuntimeError(f"Grafana query failed: {payload.get('error', payload)}")
        result = payload["data"]["result"]
        return float(result[0]["value"][1]) if result else None


_CONNECTED = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      timelineItems(itemTypes: [CONNECTED_EVENT], first: 100) {
        nodes { ... on ConnectedEvent { subject { ... on PullRequest {
          number mergedAt mergeCommit { oid } headRefName additions deletions
        } } } }
      }
    }
  }
}"""

_OBJECT = """
query($owner: String!, $name: String!, $expression: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: $expression) {
      ... on Tree { entries { name } }
      ... on Blob { text }
    }
  }
}"""


class GhCli:
    """GitHub reads through `gh` in the current repository."""

    def _graphql(self, query: str, **fields: str) -> Any:
        args = [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-F",
            "owner={owner}",
            "-F",
            "name={repo}",
        ]
        for key, value in fields.items():
            args += ["-F" if value.isdigit() else "-f", f"{key}={value}"]
        payload = json.loads(run_gh(args))
        if payload.get("errors"):
            raise RuntimeError(f"gh api graphql failed: {payload['errors']}")
        return payload["data"]["repository"]

    def connected_prs(self, issue: int) -> list[PullRequest]:
        issue_node = self._graphql(_CONNECTED, number=str(issue))["issue"]
        if issue_node is None:
            raise RuntimeError(f"no issue {issue} in this repository")
        prs = {}
        for node in issue_node["timelineItems"]["nodes"]:
            subject = (node or {}).get("subject") or {}
            if "number" not in subject:
                continue
            merged_at = subject["mergedAt"]
            prs[subject["number"]] = PullRequest(
                number=subject["number"],
                merged_at=None if merged_at is None else datetime.fromisoformat(merged_at),
                merge_commit=(subject["mergeCommit"] or {}).get("oid"),
                head_branch=subject["headRefName"],
                additions=subject["additions"],
                deletions=subject["deletions"],
            )
        return list(prs.values())

    def comments(self, pr: int) -> list[tuple[str, str]]:
        payload = json.loads(run_gh(["pr", "view", str(pr), "--json", "comments"]))
        return [((c.get("author") or {}).get("login", ""), c["body"]) for c in payload["comments"]]

    def _object(self, commit: str, path: str) -> Any:
        return self._graphql(_OBJECT, expression=f"{commit}:{path}")["object"]

    def tree(self, commit: str, path: str) -> list[str] | None:
        found = self._object(commit, path)
        return None if found is None else [entry["name"] for entry in found["entries"]]

    def blob(self, commit: str, path: str) -> str | None:
        found = self._object(commit, path)
        return None if found is None else found["text"]


def _positive(text: str) -> int:
    if not text.isdigit() or int(text) < 1:
        raise argparse.ArgumentTypeError(f"not a positive integer: {text!r}")
    return int(text)


def main(
    argv: Sequence[str],
    environ: Mapping[str, str],
    *,
    prometheus: Callable[[str, str], Prometheus] = GrafanaProxy,
    github: GitHub | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--issue", type=_positive, required=True)
    parser.add_argument("--attempt", type=_positive, default=1)
    args = parser.parse_args(argv)
    missing = [name for name in _CREDENTIALS if not environ.get(name)]
    if missing:
        print(f"error: {', '.join(missing)} not set", file=sys.stderr)
        return 2
    source = prometheus(environ["GRAFANA_URL"], environ["GRAFANA_SERVICE_ACCOUNT_TOKEN"])
    try:
        result = reading(args.issue, args.attempt, source, github or GhCli())
    except (Unreadable, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 1 if result["gaps"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
