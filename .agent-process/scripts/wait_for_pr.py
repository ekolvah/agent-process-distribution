#!/usr/bin/env python3
"""Wait until a PR's checks concluded, then report what is left for the author.

Usage: python .agent-process/scripts/wait_for_pr.py <PR> [--timeout SECONDS]

The implementing run ends only after checks and reviews: a check that has not concluded (the
`agent-review` check waiting for the requested Codex review, or running the Claude fallback,
included) is a pending review. The script reads `gh pr checks <PR> --json name,bucket,link`
every 30 s until the head reports at least one check and none is in the `pending` bucket,
then reads the unresolved review threads of either reviewer (GraphQL). The sorting is gh's
(`pkg/cmd/pr/checks/aggregate.go`, tag v2.87.3): `pass`, `skipping`, `fail`, `cancel`,
`pending` (STALE included), the latest run per name — a rerun replaces its entry.

Why `--json` and not `--watch` (`pkg/cmd/pr/checks/checks.go`): the loop exists for the
rollup that is empty for seconds after a push — gh reports it as the error `no checks
reported on the '<branch>' branch` (line 303, before the export at 184–186). The watch exits
1 on it (inside its loop too, 228–237) exactly as on a failed check (248–249), refuses
`--json` (line 81) and leaves on `Pending == 0` (218), so a script around it would loop and
re-read `--json` anyway. The `--json` read exits 0 with failed or pending checks (the export
returns first, 189–191) and non-zero only on that error or one outside the checks. Every
read is of the current head (`commits(last: 1)`); a push during the wait is followed by the
next read, and the next `wait_for_pr` of the loop sees a check that attaches after the last.

Exit 0: nothing unresolved; 1: failed or cancelled checks or unresolved threads, each printed
with its location; 2: `gh` itself failed, its stderr printed — never a verdict on the PR;
3: `--timeout` (default 30 minutes) elapsed, the line names what was still awaited.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

Gh = Callable[[list[str]], "subprocess.CompletedProcess[str]"]

DEFAULT_TIMEOUT = 30 * 60
POLL_SECONDS = 30
_NO_CHECKS = "no checks reported"
_THREADS_QUERY = (
    "query($owner:String!,$name:String!,$pr:Int!,$after:String){"
    "repository(owner:$owner,name:$name){pullRequest(number:$pr){url "
    "reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}"
    "nodes{id isResolved path line comments(first:1){nodes{author{login} body url}}}}}}}"
)


def run_gh(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """`gh` as a seam: the caller reads the exit code, `stdout` and `stderr`."""
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    if result.stdout is None or result.stderr is None:
        raise RuntimeError(f"`{' '.join(cmd)}`: broken capture (stdout or stderr is None)")
    return result


def _failure(cmd: list[str], result: subprocess.CompletedProcess[str]) -> RuntimeError:
    detail = result.stderr.strip() or "no stderr"
    return RuntimeError(f"`{' '.join(cmd)}` failed (rc={result.returncode}): {detail}")


def _json(gh: Gh, cmd: list[str]) -> Any:
    result = gh(cmd)
    if result.returncode != 0:
        raise _failure(cmd, result)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"`{' '.join(cmd)}` returned no JSON: {result.stdout!r}") from exc


def _checks(gh: Gh, pr: int) -> list[dict[str, Any]] | None:
    """The head's checks as `gh pr checks` sorts them; `None` while the rollup is empty."""
    cmd = ["gh", "pr", "checks", str(pr), "--json", "name,bucket,link"]
    result = gh(cmd)
    if result.returncode != 0:
        if _NO_CHECKS in result.stderr:
            return None
        raise _failure(cmd, result)
    try:
        return list(json.loads(result.stdout))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"`{' '.join(cmd)}` returned no JSON: {result.stdout!r}") from exc


def _unresolved_threads(gh: Gh, pr: int) -> tuple[str, list[dict[str, Any]]]:
    """The PR's URL and its unresolved review threads."""
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
        pull = _json(gh, cmd)["data"]["repository"]["pullRequest"]
        page = pull["reviewThreads"]
        threads += [t for t in page["nodes"] if not t.get("isResolved")]
        if not page["pageInfo"].get("hasNextPage"):
            return str(pull.get("url")), threads
        after = str(page["pageInfo"].get("endCursor"))


def wait_for_pr(
    pr: int,
    *,
    gh: Gh = run_gh,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    timeout: float = DEFAULT_TIMEOUT,
) -> int:
    deadline = clock() + timeout
    last: str | None = None
    while True:
        checks = _checks(gh, pr)
        pending = [str(c["name"]) for c in checks or [] if c["bucket"] == "pending"]
        if checks and not pending:
            break
        waiting = ", ".join(pending) or _NO_CHECKS
        # The timeout is elapsed time, not a count of whole poll intervals: the last sleep
        # is the remainder and the last read is at the deadline, so a rollup that never
        # fills ends here, and never before `timeout` seconds passed (PR 147, round 1).
        now = clock()
        if now >= deadline:
            print(f"timeout after {int(timeout)}s: {waiting}")
            return 3
        if waiting != last:  # one line per state, not one per poll
            print(f"waiting: {waiting}")
            last = waiting
        sleep(min(POLL_SECONDS, deadline - now))
    url, threads = _unresolved_threads(gh, pr)
    failed = [c for c in checks if c["bucket"] not in {"pass", "skipping"}]
    for check in failed:
        print(f"failed: {check['name']} {check.get('link', '')}".rstrip())
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
    print(f"clean: {len(checks)} checks green, no unresolved threads ({url})")
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
