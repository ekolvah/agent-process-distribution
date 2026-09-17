"""The merge gate fails on an unresolved P0/P1 thread of either reviewer and replies to none."""

from __future__ import annotations

import inspect
import json

import pytest

from scripts import check_blocking_review_threads
from scripts.check_blocking_review_threads import ReviewThread, blocking_threads, review_threads

CLAUDE_REVIEW_JOB = "github-actions[bot]"


def _payload(*, resolved: bool, priority: str, author: str = "chatgpt-codex-connector") -> dict:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "headRefOid": "a" * 40,
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
                    },
                }
            }
        }
    }


def test_open_codex_p1_is_merge_blocking() -> None:
    assert blocking_threads(_payload(resolved=False, priority="P1")) == [
        ("thread-1", "P1", "https://example.test/thread-1")
    ]


def test_open_p1_by_the_claude_review_job_is_merge_blocking() -> None:
    """The Claude action comments under the workflow token (ADR 0004), so its
    findings carry the github-actions login; the gate reads both reviewers."""
    assert blocking_threads(_payload(resolved=False, priority="P1", author=CLAUDE_REVIEW_JOB)) == [
        ("thread-1", "P1", "https://example.test/thread-1")
    ]


def test_open_p2_by_the_claude_review_job_is_not_blocking() -> None:
    assert blocking_threads(_payload(resolved=False, priority="P2", author=CLAUDE_REVIEW_JOB)) == []


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
        )
    ]


def _record_gh(monkeypatch: pytest.MonkeyPatch, payload: dict) -> list[list[str]]:
    calls: list[list[str]] = []

    def run_gh(args: list[str]) -> str:
        calls.append(list(args))
        return json.dumps(payload)

    monkeypatch.setattr(check_blocking_review_threads, "run_gh", run_gh)
    return calls


def test_main_fails_on_an_unresolved_p1_without_replying(monkeypatch, capsys) -> None:
    calls = _record_gh(monkeypatch, _payload(resolved=False, priority="P1"))

    with pytest.raises(SystemExit) as exit_info:
        check_blocking_review_threads.main(["--repo", "owner/repo", "--pr", "17"])

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "unresolved P0/P1 review threads" in captured.err
    assert "https://example.test/thread-1" in captured.err
    assert len(calls) == 1
    assert not any("/replies" in argument for call in calls for argument in call)


def test_main_passes_once_the_p1_thread_is_resolved(monkeypatch, capsys) -> None:
    calls = _record_gh(monkeypatch, _payload(resolved=True, priority="P1"))

    check_blocking_review_threads.main(["--repo", "owner/repo", "--pr", "17"])

    assert "ok: no unresolved P0/P1 review threads" in capsys.readouterr().out
    assert len(calls) == 1


def test_the_required_check_never_resolves_a_thread() -> None:
    """ADR 0022/0027: the required check reads; it never resolves or classifies a thread."""
    source = inspect.getsource(check_blocking_review_threads)
    assert "resolveReviewThread" not in source
    assert "resolve_review_thread" not in source
