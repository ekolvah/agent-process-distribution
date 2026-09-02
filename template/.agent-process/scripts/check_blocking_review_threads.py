#!/usr/bin/env python3
"""Label Codex findings clearly and fail on unresolved blocking conversations.

GitHub's native ``required_conversation_resolution`` setting is intentionally
not used here: it treats advisory and blocking threads identically. This check
implements the narrower merge contract promised by REVIEW_CONTRACT.md.
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

_CODEX_REVIEWER = "chatgpt-codex-connector"
_PRIORITY = re.compile(r"\bP(?P<number>[0-3])\b", re.IGNORECASE)
_CLASSIFICATION_MARKER = "<!-- agent-review-merge-classification -->"
_QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      reviewThreads(first: 100) {
        pageInfo { hasNextPage }
        nodes {
          id
          isResolved
          comments(first: 100) {
            pageInfo { hasNextPage }
            nodes { databaseId body url replyTo { id } author { login } }
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
    classified: bool


def _normalise_login(value: object) -> str:
    return str(value or "").removesuffix("[bot]").lower()


def review_threads(payload: object) -> list[ReviewThread]:
    """Return open Codex findings with their user-facing merge classification."""
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
        classified = any(
            isinstance(comment, Mapping)
            and isinstance(comment.get("body"), str)
            and _CLASSIFICATION_MARKER in comment["body"]
            for comment in records
        )
        for comment in records:
            if not isinstance(comment, Mapping) or comment.get("replyTo") is not None:
                continue
            author = comment.get("author")
            login = author.get("login") if isinstance(author, Mapping) else None
            body = comment.get("body")
            priority = _PRIORITY.search(body) if isinstance(body, str) else None
            if _normalise_login(login) != _CODEX_REVIEWER or priority is None:
                continue
            comment_id = comment.get("databaseId")
            if not isinstance(comment_id, int):
                raise RuntimeError("a Codex review comment has no database ID")
            result.append(
                ReviewThread(
                    thread_id=str(thread.get("id", "unknown")),
                    comment_id=comment_id,
                    priority=priority.group(0).upper(),
                    url=str(comment.get("url", "")),
                    blocking=priority.group("number") in {"0", "1"},
                    classified=classified,
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


def _publish_classifications(repository: str, pr_number: int, threads: list[ReviewThread]) -> None:
    for thread in threads:
        if thread.classified:
            continue
        message = (
            "**BLOCKING** — this finding must be fixed and this conversation resolved before merge."
            if thread.blocking
            else "**NON-BLOCKING** — this finding is advisory and does not prevent merge."
        )
        run_gh(
            [
                "api",
                "--method",
                "POST",
                f"repos/{repository}/pulls/{pr_number}/comments/{thread.comment_id}/replies",
                "-f",
                f"body={_CLASSIFICATION_MARKER}\n{message}",
            ]
        )


def _parse_options(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", required=True, metavar="OWNER/REPO")
    parser.add_argument("--pr", required=True, type=int, metavar="NUMBER")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    options = _parse_options(argv)
    try:
        owner, name = options.repo.split("/", 1)
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
                f"number={options.pr}",
            ]
        )
        threads = review_threads(json.loads(raw))
        _publish_classifications(options.repo, options.pr, threads)
        findings = [thread for thread in threads if thread.blocking]
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot determine unresolved blocking review threads: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if findings:
        print("error: unresolved BLOCKING Codex review conversations:", file=sys.stderr)
        for thread in findings:
            print(f"- BLOCKING: {thread.url or thread.thread_id}", file=sys.stderr)
        raise SystemExit(1)
    print("ok: no unresolved BLOCKING Codex review conversations")


if __name__ == "__main__":
    main()
