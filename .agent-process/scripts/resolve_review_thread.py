#!/usr/bin/env python3
"""Resolve one BLOCKING review thread the fixer's own correction addressed.

CI never infers whether a finding was addressed (ADR 0022): the required
check (`check_blocking_review_threads.py`) answers "may this PR merge?" from
the workflow token, and this script answers "I, the fixer, addressed this
finding" from the maintainer's authenticated local session. Different actor,
credential, and trigger — never wired into a workflow.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence

try:
    from scripts.check_blocking_review_threads import blocking_threads, review_threads
    from scripts.gh_io import run_gh
except ModuleNotFoundError:  # Direct execution from the relocated payload.
    from check_blocking_review_threads import blocking_threads, review_threads
    from gh_io import run_gh

_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      headRefOid
      reviewThreads(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          id
          isResolved
          comments(first: 100) {
            pageInfo { hasNextPage }
            nodes { databaseId body url replyTo { id } author { login } originalCommit { oid } }
          }
        }
      }
    }
  }
}
"""

_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { isResolved }
  }
}
"""


def _fetch(repo: str, pr: int) -> dict:
    owner, name = repo.split("/", 1)
    raw = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={_QUERY}",
            "-F",
            f"owner={owner}",
            "-F",
            f"name={name}",
            "-F",
            f"number={pr}",
        ]
    )
    return json.loads(raw)


def _head_ref_oid(payload: dict) -> str:
    return str(payload["data"]["repository"]["pullRequest"]["headRefOid"])


def list_blocking(payload: dict) -> list[tuple[str, str, str]]:
    """Return `(thread_id, priority, url)` for every open BLOCKING thread."""
    return blocking_threads(payload)


def resolve(payload: dict, thread_id: str, *, mutate: Callable[[str], object]) -> None:
    """Resolve `thread_id`, refusing a thread reported against the current head.

    `mutate(thread_id) -> object` issues the `resolveReviewThread` mutation and
    returns its decoded response; injected so a test can stub the transport
    (§II) and so a `gh` exit 0 is never trusted without re-reading `isResolved`.
    """
    head = _head_ref_oid(payload)
    threads = {thread.thread_id: thread for thread in review_threads(payload)}
    thread = threads.get(thread_id)
    if thread is None:
        raise RuntimeError(f"no open review thread {thread_id!r} on this PR")
    if thread.original_commit_oid is None:
        raise RuntimeError(
            f"review thread {thread_id} has no originalCommit.oid — refusing to resolve blind"
        )
    if thread.original_commit_oid == head:
        raise RuntimeError(
            f"review thread {thread_id} was reported against the current head {head} — "
            "nothing has been pushed past the reviewed commit yet"
        )
    response = mutate(thread_id)
    resolved = (
        isinstance(response, dict)
        and isinstance(response.get("data"), dict)
        and isinstance(response["data"].get("resolveReviewThread"), dict)
        and isinstance(response["data"]["resolveReviewThread"].get("thread"), dict)
        and response["data"]["resolveReviewThread"]["thread"].get("isResolved") is True
    )
    if not resolved:
        raise RuntimeError(
            f"resolveReviewThread for {thread_id} did not report isResolved: true — "
            f"treat the thread as still open: {response!r}"
        )


def _gh_mutate(thread_id: str) -> dict:
    raw = run_gh(["api", "graphql", "-f", f"query={_MUTATION}", "-F", f"threadId={thread_id}"])
    return json.loads(raw)


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="OWNER/REPO")
    parser.add_argument("--pr", required=True, type=int, metavar="NUMBER")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="print every open BLOCKING thread")
    group.add_argument("--thread", metavar="NODE-ID", help="resolve this thread")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    options = _parse_options(list(sys.argv[1:] if argv is None else argv))
    try:
        payload = _fetch(options.repo, options.pr)
        if options.list:
            for thread_id, priority, url in list_blocking(payload):
                print(f"{priority}\t{thread_id}\t{url}")
            return
        resolve(payload, options.thread, mutate=_gh_mutate)
        print(f"ok: resolved {options.thread}")
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
