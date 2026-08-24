"""The manual Codex carrier translates GitHub-native review records."""

from __future__ import annotations

import pytest

from scripts import request_codex_review
from scripts.request_codex_review import find_verdict, poll_for_verdict

_HEAD = "a" * 40
_REVIEWER = "chatgpt-codex-connector[bot]"


def _review(state: str) -> dict[str, object]:
    return {
        "id": 42,
        "user": {"login": _REVIEWER},
        "commit_id": _HEAD,
        "state": state,
        "body": "### Codex Review",
    }


def _comment(body: str) -> dict[str, object]:
    return {"pull_request_review_id": 42, "body": body}


def test_standard_codex_p1_comment_is_blocking_evidence() -> None:
    verdict = find_verdict(
        [_review("COMMENTED")],
        [_comment("**![P1 Badge](https://example.test/p1) Preserve trusted policy")],
        _HEAD,
        _REVIEWER,
    )

    assert verdict == {
        "outcome": "blocking",
        "findings": [
            {
                "severity": "blocking",
                "confidence": "high",
                "summary": "**![P1 Badge](https://example.test/p1) Preserve trusted policy",
            }
        ],
    }


def test_standard_codex_p2_comment_is_rework_evidence() -> None:
    verdict = find_verdict(
        [_review("COMMENTED")],
        [_comment("**![P2 Badge](https://example.test/p2) Update guidance")],
        _HEAD,
        _REVIEWER,
    )

    assert verdict is not None
    assert verdict["outcome"] == "rework"
    assert verdict["findings"][0]["severity"] == "should-fix"


def test_only_current_head_codex_review_is_accepted() -> None:
    stale = {**_review("APPROVED"), "commit_id": "b" * 40}

    assert find_verdict([stale], [], _HEAD, _REVIEWER) is None


def test_poll_stops_when_a_current_head_review_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = iter((0.0, 1.0))
    monkeypatch.setattr(
        request_codex_review, "_fetch_reviews", lambda *_args: [_review("COMMENTED")]
    )
    monkeypatch.setattr(request_codex_review, "_fetch_review_comments", lambda *_args: [])

    assert (
        poll_for_verdict(
            "owner/repo",
            "14",
            _HEAD,
            timeout_seconds=60,
            poll_seconds=1,
            sleep=lambda _seconds: None,
            monotonic=lambda: next(clock),
        )
        is None
    )
