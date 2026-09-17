#!/usr/bin/env python3
"""Fail the review check while an unresolved P0/P1 thread of either reviewer exists.

GitHub's native ``required_conversation_resolution`` setting is intentionally
not used here: it treats advisory and blocking threads identically. This check
reads only the label of a thread's first comment — by the Codex app or by the
Claude review job, which comments under the workflow token — and whether the
thread is resolved; it replies to nothing and resolves nothing (ADR 0027).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import NamedTuple

try:
    from scripts.gh_io import run_gh
except ModuleNotFoundError:  # Direct execution from the relocated payload.
    from gh_io import run_gh

_REVIEWERS = frozenset({"chatgpt-codex-connector", "github-actions"})
_PRIORITY = re.compile(r"\bP(?P<number>[0-3])\b", re.IGNORECASE)
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


class ReviewThread(NamedTuple):
    thread_id: str
    comment_id: int
    priority: str
    url: str
    blocking: bool
    original_commit_oid: str | None = None


def _normalise_login(value: object) -> str:
    return str(value or "").removesuffix("[bot]").lower()


def fetch_review_threads(repo: str, pr: int) -> dict:
    """Run the shared review-threads GraphQL query. The one reader this required
    check and the fixer's local thread-resolve entry point both read through, so
    the thread fields, pagination handling, and request shape never diverge.
    """
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


def head_ref_oid(payload: object) -> str:
    if not isinstance(payload, Mapping):
        raise RuntimeError("GraphQL payload is not an object")
    data = payload.get("data")
    if not isinstance(data, Mapping) or not isinstance(data.get("repository"), Mapping):
        raise RuntimeError("GraphQL payload has no repository")
    pull = data["repository"].get("pullRequest")
    if not isinstance(pull, Mapping):
        raise RuntimeError("GraphQL payload has no pull request")
    return str(pull["headRefOid"])


def review_threads(payload: object) -> list[ReviewThread]:
    """Return the open threads whose first comment is a labelled reviewer finding."""
    if not isinstance(payload, Mapping):
        raise RuntimeError("GraphQL payload is not an object")
    data = payload.get("data")
    if not isinstance(data, Mapping) or not isinstance(data.get("repository"), Mapping):
        raise RuntimeError("GraphQL payload has no repository")
    pull = data["repository"].get("pullRequest")
    if not isinstance(pull, Mapping) or not isinstance(pull.get("reviewThreads"), Mapping):
        raise RuntimeError("GraphQL payload has no review threads")
    threads = pull["reviewThreads"]
    page_info = threads.get("pageInfo")
    if isinstance(page_info, Mapping) and page_info.get("hasNextPage"):
        raise RuntimeError("more than 100 review threads; refusing an incomplete merge verdict")
    nodes = threads.get("nodes")
    if not isinstance(nodes, list):
        raise RuntimeError("GraphQL review threads are not a list")

    result: list[ReviewThread] = []
    for thread in nodes:
        if not isinstance(thread, Mapping) or thread.get("isResolved"):
            continue
        comments = thread.get("comments")
        if not isinstance(comments, Mapping):
            raise RuntimeError("GraphQL thread has no comments")
        comment_page = comments.get("pageInfo")
        if isinstance(comment_page, Mapping) and comment_page.get("hasNextPage"):
            raise RuntimeError("a review thread has more than 100 comments")
        records = comments.get("nodes")
        if not isinstance(records, list):
            raise RuntimeError("GraphQL comments are not a list")
        for comment in records:
            if not isinstance(comment, Mapping) or comment.get("replyTo") is not None:
                continue
            author = comment.get("author")
            login = author.get("login") if isinstance(author, Mapping) else None
            body = comment.get("body")
            priority = _PRIORITY.search(body) if isinstance(body, str) else None
            if _normalise_login(login) not in _REVIEWERS or priority is None:
                continue
            comment_id = comment.get("databaseId")
            if not isinstance(comment_id, int):
                raise RuntimeError("a review comment has no database ID")
            original_commit = comment.get("originalCommit")
            original_commit_oid = (
                original_commit.get("oid") if isinstance(original_commit, Mapping) else None
            )
            result.append(
                ReviewThread(
                    thread_id=str(thread.get("id", "unknown")),
                    comment_id=comment_id,
                    priority=priority.group(0).upper(),
                    url=str(comment.get("url", "")),
                    blocking=priority.group("number") in {"0", "1"},
                    original_commit_oid=(
                        str(original_commit_oid) if isinstance(original_commit_oid, str) else None
                    ),
                )
            )
            break
    return result


def blocking_threads(payload: object) -> list[tuple[str, str, str]]:
    """Return ``(thread_id, priority, url)`` for open blocking threads."""
    return [
        (thread.thread_id, thread.priority, thread.url)
        for thread in review_threads(payload)
        if thread.blocking
    ]


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="OWNER/REPO")
    parser.add_argument("--pr", required=True, type=int, metavar="NUMBER")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    options = _parse_options(argv)
    try:
        unresolved = blocking_threads(fetch_review_threads(options.repo, options.pr))
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot determine unresolved P0/P1 review threads: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if unresolved:
        print("error: unresolved P0/P1 review threads:", file=sys.stderr)
        for thread_id, priority, url in unresolved:
            print(f"- {priority}: {url or thread_id}", file=sys.stderr)
        raise SystemExit(1)
    print("ok: no unresolved P0/P1 review threads")


if __name__ == "__main__":
    main()
