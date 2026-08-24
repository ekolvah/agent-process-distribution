"""The merge gate distinguishes open blocking and advisory Codex threads."""

from __future__ import annotations

from scripts.check_blocking_review_threads import blocking_threads


def _payload(*, resolved: bool, priority: str, author: str = "chatgpt-codex-connector") -> dict:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": [
                            {
                                "id": "thread-1",
                                "isResolved": resolved,
                                "comments": {
                                    "pageInfo": {"hasNextPage": False},
                                    "nodes": [
                                        {
                                            "body": f"{priority} finding",
                                            "url": "https://example.test/thread-1",
                                            "replyTo": None,
                                            "author": {"login": author},
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                }
            }
        }
    }


def test_open_codex_p1_is_merge_blocking() -> None:
    assert blocking_threads(_payload(resolved=False, priority="P1")) == [
        ("thread-1", "P1", "https://example.test/thread-1")
    ]


def test_resolved_or_nonblocking_threads_are_not_merge_blocking() -> None:
    assert blocking_threads(_payload(resolved=True, priority="P0")) == []
    assert blocking_threads(_payload(resolved=False, priority="P2")) == []


def test_human_priority_text_cannot_block_the_codex_gate() -> None:
    assert blocking_threads(_payload(resolved=False, priority="P1", author="author")) == []
