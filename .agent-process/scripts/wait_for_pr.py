#!/usr/bin/env python3
"""Wait until a PR's checks concluded, then report what is left for the author.

Usage: python .agent-process/scripts/wait_for_pr.py <PR> [--timeout SECONDS]

The implementing run ends only after checks and reviews: a running check (the `agent-review`
check waiting for the requested Codex review included) is a pending review, so the script
polls `gh pr view --json statusCheckRollup` until every check on the head concluded and
only then reads the unresolved review threads. Exit 0: nothing unresolved; 1: failed checks
or unresolved threads, each printed with its location; 3: `--timeout` (default 30 minutes)
elapsed while something was still running. Stays until `v2-4` reworks review.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

Gh = Callable[[list[str]], str]

DEFAULT_TIMEOUT = 30 * 60
POLL_SECONDS = 30
_GREEN = {"SUCCESS", "NEUTRAL", "SKIPPED"}
_THREADS_QUERY = (
    "query($owner:String!,$name:String!,$pr:Int!,$after:String){"
    "repository(owner:$owner,name:$name){pullRequest(number:$pr){"
    "reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}"
    "nodes{id isResolved path line comments(first:1){nodes{author{login} body url}}}}}}}"
)


def run_gh(cmd: list[str]) -> str:
    result = subprocess.run(cmd, text=True, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        detail = (result.stderr or "").strip() or "no stderr"
        raise RuntimeError(f"`{' '.join(cmd)}` failed (rc={result.returncode}): {detail}")
    return result.stdout or ""


def _json(gh: Gh, cmd: list[str]) -> Any:
    out = gh(cmd)
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"`{' '.join(cmd)}` returned no JSON: {out!r}") from exc


def _concluded(check: dict[str, Any]) -> bool:
    if check.get("__typename") == "StatusContext":
        return check.get("state") not in {"PENDING", "EXPECTED"}
    return check.get("status") == "COMPLETED"


def _failed(check: dict[str, Any]) -> bool:
    if check.get("__typename") == "StatusContext":
        return check.get("state") != "SUCCESS"
    return check.get("conclusion") not in _GREEN


def _name(check: dict[str, Any]) -> str:
    return str(check.get("name") or check.get("context") or check.get("workflowName") or "?")


def _url(check: dict[str, Any]) -> str:
    return str(check.get("detailsUrl") or check.get("targetUrl") or "")


def _unresolved_threads(gh: Gh, pr: int) -> list[dict[str, Any]]:
    repo = _json(gh, ["gh", "repo", "view", "--json", "owner,name"])
    owner, name = str(repo["owner"]["login"]), str(repo["name"])
    threads: list[dict[str, Any]] = []
    after: str | None = None
    while True:
        cmd = [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={_THREADS_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"pr={pr}",
        ]
        if after:
            cmd += ["-F", f"after={after}"]
        page = _json(gh, cmd)["data"]["repository"]["pullRequest"]["reviewThreads"]
        threads += [t for t in page["nodes"] if not t.get("isResolved")]
        if not page["pageInfo"].get("hasNextPage"):
            return threads
        after = str(page["pageInfo"].get("endCursor"))


def wait_for_pr(
    pr: int,
    *,
    gh: Gh = run_gh,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    timeout: float = DEFAULT_TIMEOUT,
) -> int:
    start = clock()
    while True:
        view = _json(
            gh, ["gh", "pr", "view", str(pr), "--json", "statusCheckRollup,headRefOid,url"]
        )
        checks: list[dict[str, Any]] = view.get("statusCheckRollup") or []
        pending = [c for c in checks if not _concluded(c)]
        if not pending:
            break
        if clock() - start >= timeout:
            names = ", ".join(_name(c) for c in pending)
            print(
                f"timeout after {int(timeout)}s; still running on {view.get('headRefOid')}: {names}"
            )
            return 3
        sleep(POLL_SECONDS)
    if not checks:
        print(f"no checks on {view.get('headRefOid')} ({view.get('url')})")
    failed = [c for c in checks if _failed(c)]
    for check in failed:
        print(f"failed: {_name(check)} {_url(check)}".rstrip())
    threads = _unresolved_threads(gh, pr)
    for thread in threads:
        first = (thread.get("comments") or {}).get("nodes") or [{}]
        comment = first[0]
        author = (comment.get("author") or {}).get("login", "?")
        body = str(comment.get("body") or "").strip().splitlines() or [""]
        print(
            f"unresolved: {thread.get('path')}:{thread.get('line')} [{author}] {body[0]} {comment.get('url', '')}"
        )
    if failed or threads:
        return 1
    print(f"clean: {len(checks)} checks green, no unresolved threads ({view.get('url')})")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr", type=int, help="pull request number")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds; default 1800"
    )
    ns = parser.parse_args(argv)
    try:
        sys.exit(wait_for_pr(ns.pr, timeout=ns.timeout))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
