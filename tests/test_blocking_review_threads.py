"""The merge gate distinguishes open blocking and advisory Codex threads."""

from __future__ import annotations

from scripts import check_blocking_review_threads
from scripts.check_blocking_review_threads import ReviewThread, blocking_threads, review_threads


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
                                            "databaseId": 101,
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


def test_open_p2_is_explicitly_nonblocking() -> None:
    assert review_threads(_payload(resolved=False, priority="P2")) == [
        ReviewThread(
            thread_id="thread-1",
            comment_id=101,
            priority="P2",
            url="https://example.test/thread-1",
            blocking=False,
            classified=False,
        )
    ]


def test_classification_reply_uses_plain_merge_language(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        check_blocking_review_threads,
        "run_gh",
        lambda args: calls.append(args) or "{}",
    )

    check_blocking_review_threads._publish_classifications(
        "owner/repo",
        17,
        [ReviewThread("thread-1", 101, "P1", "https://example.test/thread-1", True, False)],
    )

    assert len(calls) == 1
    assert any("**BLOCKING**" in argument for argument in calls[0])
    assert not any("P1" in argument for argument in calls[0])
