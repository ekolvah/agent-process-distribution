"""The fixer resolves the BLOCKING thread its own correction addressed (ADR 0022)."""

from __future__ import annotations

import pytest

from scripts.resolve_review_thread import list_blocking, resolve

_HEAD = "4165198873b01503d9c2e33436cc5d94f98b017d"  # pragma: allowlist secret
_BEHIND = "98cd7850000000000000000000000000000000"  # pragma: allowlist secret


def _thread(
    thread_id: str,
    *,
    priority: str,
    original_commit_oid: str | None,
    resolved: bool = False,
    author: str = "chatgpt-codex-connector",
) -> dict:
    return {
        "id": thread_id,
        "isResolved": resolved,
        "comments": {
            "pageInfo": {"hasNextPage": False},
            "nodes": [
                {
                    "databaseId": 1,
                    "body": f"{priority} finding",
                    "url": f"https://example.test/{thread_id}",
                    "replyTo": None,
                    "author": {"login": author},
                    "originalCommit": (
                        {"oid": original_commit_oid} if original_commit_oid is not None else None
                    ),
                }
            ],
        },
    }


def _payload(*, head: str = _HEAD, threads: list[dict]) -> dict:
    return {
        "data": {
            "repository": {
                "pullRequest": {
                    "headRefOid": head,
                    "reviewThreads": {
                        "pageInfo": {"hasNextPage": False},
                        "nodes": threads,
                    },
                }
            }
        }
    }


def test_list_reports_every_open_blocking_thread_with_its_node_id() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])

    assert list_blocking(payload) == [("thread-1", "P1", "https://example.test/thread-1")]


def test_list_omits_resolved_and_non_blocking_threads() -> None:
    payload = _payload(
        threads=[
            _thread("resolved", priority="P1", original_commit_oid=_BEHIND, resolved=True),
            _thread("advisory", priority="P2", original_commit_oid=_BEHIND),
        ]
    )

    assert list_blocking(payload) == []


def test_resolve_issues_the_mutation_and_verifies_the_reported_state() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    def mutate(thread_id: str) -> dict:
        calls.append(thread_id)
        return {"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}}

    resolve(payload, "thread-1", mutate=mutate)

    assert calls == ["thread-1"]


def test_resolve_refuses_a_thread_reported_against_the_current_head() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_HEAD)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="current head"):
        resolve(payload, "thread-1", mutate=lambda thread_id: calls.append(thread_id))

    assert calls == []


def test_resolve_refuses_a_thread_with_no_original_commit() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=None)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="originalCommit"):
        resolve(payload, "thread-1", mutate=lambda thread_id: calls.append(thread_id))

    assert calls == []


def test_resolve_refuses_a_non_blocking_thread() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P2", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="not BLOCKING"):
        resolve(payload, "thread-1", mutate=lambda thread_id: calls.append(thread_id))

    assert calls == []


def test_a_mutation_reporting_an_unresolved_thread_fails_loudly() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])

    def mutate(thread_id: str) -> dict:
        return {"data": {"resolveReviewThread": {"thread": {"isResolved": False}}}}

    with pytest.raises(RuntimeError, match="isResolved"):
        resolve(payload, "thread-1", mutate=mutate)
