#!/usr/bin/env python3
"""Fail when an unresolved Codex P0/P1 conversation remains on a pull request.

GitHub's native ``required_conversation_resolution`` setting is intentionally
not used here: it treats an advisory P2/P3 thread exactly like a merge-blocking
P0/P1.  This check is the narrower contract promised by REVIEW_CONTRACT.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence

from scripts.gh_io import run_gh

_CODEX_REVIEWER = "chatgpt-codex-connector"
_BLOCKING_PRIORITY = re.compile(r"\bP[01]\b", re.IGNORECASE)
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
            nodes { body url replyTo { id } author { login } }
          }
        }
      }
    }
  }
}
"""


def _normalise_login(value: object) -> str:
    return str(value or "").removesuffix("[bot]").lower()


def blocking_threads(payload: object) -> list[tuple[str, str, str]]:
    """Return ``(thread_id, priority, url)`` for open, merge-blocking threads."""
    if not isinstance(payload, Mapping):
        raise RuntimeError("GraphQL payload is not an object")
    repository = payload.get("data")
    if not isinstance(repository, Mapping) or not isinstance(repository.get("repository"), Mapping):
        raise RuntimeError("GraphQL payload has no repository")
    pull = repository["repository"].get("pullRequest")
    if not isinstance(pull, Mapping) or not isinstance(pull.get("reviewThreads"), Mapping):
        raise RuntimeError("GraphQL payload has no review threads")
    threads = pull["reviewThreads"]
    page_info = threads.get("pageInfo")
    if isinstance(page_info, Mapping) and page_info.get("hasNextPage"):
        raise RuntimeError("more than 100 review threads; refusing an incomplete merge verdict")
    nodes = threads.get("nodes")
    if not isinstance(nodes, list):
        raise RuntimeError("GraphQL review threads are not a list")

    result: list[tuple[str, str, str]] = []
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
            priority = _BLOCKING_PRIORITY.search(body) if isinstance(body, str) else None
            if _normalise_login(login) == _CODEX_REVIEWER and priority:
                result.append(
                    (
                        str(thread.get("id", "unknown")),
                        priority.group(0).upper(),
                        str(comment.get("url", "")),
                    )
                )
                break
    return result


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
        findings = blocking_threads(json.loads(raw))
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: cannot determine unresolved blocking review threads: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if findings:
        print("error: unresolved BLOCKING Codex review conversations:", file=sys.stderr)
        for thread_id, priority, url in findings:
            print(f"- BLOCKING — {priority}: {url or thread_id}", file=sys.stderr)
        raise SystemExit(1)
    print("ok: no unresolved BLOCKING Codex P0/P1 review conversations")


if __name__ == "__main__":
    main()
