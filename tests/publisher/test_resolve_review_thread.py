"""The fixer resolves the BLOCKING thread its own correction addressed (ADR 0022)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MOVED = _ROOT / "skills" / "agent-process" / "scripts" / "resolve_review_thread.py"
if _MOVED.is_file():
    _spec = importlib.util.spec_from_file_location("agent_process_resolve_review_thread", _MOVED)
    assert _spec and _spec.loader
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_spec.name] = _module
    _spec.loader.exec_module(_module)
else:  # RED commit: the source has not moved yet.
    from scripts import resolve_review_thread as _module

close_round = _module.close_round
list_blocking = _module.list_blocking
resolve = _module.resolve

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


def test_list_blocking_includes_a_p1_by_the_claude_review_job() -> None:
    """Scenario: Addressed finding of either reviewer — the fixer resolves a P0/P1
    raised by the Claude review job (github-actions login) as it does a Codex one."""
    payload = _payload(
        threads=[
            _thread(
                "claude-p1",
                priority="P1",
                original_commit_oid=_BEHIND,
                author="github-actions[bot]",
            ),
            _thread(
                "claude-p2",
                priority="P2",
                original_commit_oid=_BEHIND,
                author="github-actions[bot]",
            ),
        ]
    )

    assert list_blocking(payload) == [("claude-p1", "P1", "https://example.test/claude-p1")]


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


# Scenario: Blocking thread addressed — the step after the wait is one command:
# the head's `agent-review` run concluded (the review of the head is in, Codex's or
# the fallback's), resolve, re-run that run (a resolve has no event of its own,
# and the required context is the head's `pull_request` run), reply. The order
# lives in code, not in a sentence copied to five places.


def _round(*, status: str | None, calls: list[str]) -> dict:
    def head_run(head: str) -> tuple[int, str] | None:
        calls.append(f"head-run {head[:7]}")
        return None if status is None else (35, status)

    def mutate(thread_id: str) -> dict:
        calls.append(f"resolve {thread_id}")
        return {"data": {"resolveReviewThread": {"thread": {"isResolved": True}}}}

    def rerun(run_id: int) -> None:
        calls.append(f"rerun {run_id}")

    def post_reply(comment_id: int, body: str) -> None:
        calls.append(f"reply {comment_id} {body}")

    return {
        "repo": "ekolvah/agent-process-distribution",
        "pr": 140,
        "head_run": head_run,
        "mutate": mutate,
        "rerun": rerun,
        "post_reply": post_reply,
    }


# The recovery command is pasted, not reconstructed (D3, Codex's P2 on PR 140).
_REPLY_CALL = "repos/ekolvah/agent-process-distribution/pulls/140/comments/1/replies"


def test_close_round_resolves_reruns_the_head_run_and_replies_in_that_order() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    run_id = close_round(
        payload, "thread-1", "fixed in abc1234", **_round(status="completed", calls=calls)
    )

    assert run_id == 35
    assert calls == [
        f"head-run {_HEAD[:7]}",
        "resolve thread-1",
        "rerun 35",
        "reply 1 fixed in abc1234",
    ]


def test_close_round_refuses_while_the_head_run_is_still_running() -> None:
    """The wait is on the concluded check, whichever carrier reviewed the head."""
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="in_progress"):
        close_round(payload, "thread-1", "fixed", **_round(status="in_progress", calls=calls))

    assert calls == [f"head-run {_HEAD[:7]}"]


def test_close_round_refuses_without_a_head_run() -> None:
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="no `agent-review` run"):
        close_round(payload, "thread-1", "fixed", **_round(status=None, calls=calls))

    assert calls == [f"head-run {_HEAD[:7]}"]


def _failing(transports: dict, name: str) -> dict:
    def fail(*_args: object) -> None:
        raise RuntimeError(f"gh {name} failed: 502")

    return {**transports, name: fail}


def test_close_round_names_the_rerun_and_the_reply_when_the_rerun_fails() -> None:
    """D3 (issue 139): after a successful resolve the thread is gone from `--list`
    and `--thread` cannot be retried; the error names what is still undone with
    the ids filled in — here the rerun and the reply — and nothing after the
    failure runs."""
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError) as failure:
        close_round(
            payload,
            "thread-1",
            "fixed",
            **_failing(_round(status="completed", calls=calls), "rerun"),
        )

    message = str(failure.value)
    assert "gh run rerun 35" in message
    assert _REPLY_CALL in message
    assert "<owner" not in message and "<pr>" not in message
    # `gh api -f` sends a static string; only `-F` reads a leading `@` as a file
    # (Codex's P1 on PR 140).
    assert "-F body=@" in message
    assert "-f body=" not in message
    assert "502" in message
    assert calls == [f"head-run {_HEAD[:7]}", "resolve thread-1"]


def test_close_round_names_the_reply_alone_when_the_reply_fails() -> None:
    """The rerun went through: a second `gh run rerun` of a run in progress is
    refused, so the error names the reply alone."""
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError) as failure:
        close_round(
            payload,
            "thread-1",
            "fixed",
            **_failing(_round(status="completed", calls=calls), "post_reply"),
        )

    message = str(failure.value)
    assert _REPLY_CALL in message
    assert "<owner" not in message and "<pr>" not in message
    assert "-F body=@" in message
    assert "gh run rerun" not in message
    assert "502" in message
    assert calls == [f"head-run {_HEAD[:7]}", "resolve thread-1", "rerun 35"]


def test_close_round_refuses_an_unknown_thread_before_any_write() -> None:
    """A mistyped or already-resolved thread id is the `error:` line of the resolve
    guard, not a KeyError of the reply lookup (Codex's P2 on PR 140)."""
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="no open review thread"):
        close_round(payload, "thread-9", "fixed", **_round(status="completed", calls=calls))

    assert calls == [f"head-run {_HEAD[:7]}"]


def test_close_round_refuses_an_empty_reply() -> None:
    """A resolve is never the last write on a thread."""
    payload = _payload(threads=[_thread("thread-1", priority="P1", original_commit_oid=_BEHIND)])
    calls: list[str] = []

    with pytest.raises(RuntimeError, match="reply"):
        close_round(payload, "thread-1", "  \n", **_round(status="completed", calls=calls))

    assert calls == []
