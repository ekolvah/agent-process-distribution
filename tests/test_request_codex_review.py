"""Codex fallback must carry the same structured evidence as Claude."""

from __future__ import annotations

import json

import pytest

from scripts import request_codex_review
from scripts.request_codex_review import find_verdict, poll_for_verdict

_HEAD = "a" * 40
_REVIEWER = "chatgpt-codex-connector[bot]"


def _review(state: str, body: str) -> list[dict[str, object]]:
    return [
        {
            "user": {"login": _REVIEWER},
            "commit_id": _HEAD,
            "state": state,
            "body": body,
        }
    ]


def test_codex_review_returns_the_same_structured_evidence() -> None:
    evidence = find_verdict(
        _review(
            "CHANGES_REQUESTED",
            """Found a merge-blocking defect.

<!-- agent-review-evidence
{"outcome":"blocking","findings":[{"severity":"blocking","confidence":"high","summary":"The verifier accepts a blocking outcome without a finding."}]}
-->""",
        ),
        _HEAD,
        _REVIEWER,
    )

    assert evidence == {
        "outcome": "blocking",
        "findings": [
            {
                "severity": "blocking",
                "confidence": "high",
                "summary": "The verifier accepts a blocking outcome without a finding.",
            }
        ],
    }


def test_codex_review_without_structured_evidence_is_unavailable() -> None:
    assert find_verdict(_review("CHANGES_REQUESTED", "Please fix this."), _HEAD, _REVIEWER) is None


def test_codex_evidence_outcome_must_match_its_review_state() -> None:
    assert (
        find_verdict(
            _review(
                "APPROVED",
                """<!-- agent-review-evidence
{"outcome":"blocking","findings":[{"severity":"blocking","confidence":"high","summary":"Mismatched evidence."}]}
-->""",
            ),
            _HEAD,
            _REVIEWER,
        )
        is None
    )


def test_poll_for_verdict_never_posts_a_codex_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[object] = []
    clock = iter((0.0, 1.0))
    monkeypatch.setattr(request_codex_review, "_fetch_reviews", lambda *_args: [])
    monkeypatch.setattr(request_codex_review, "run_gh", requests.append, raising=False)

    verdict = poll_for_verdict(
        "owner/repo",
        "14",
        _HEAD,
        timeout_seconds=1,
        poll_seconds=1,
        sleep=lambda _seconds: None,
        monotonic=lambda: next(clock),
    )

    assert verdict is None
    assert requests == []
    assert not hasattr(request_codex_review, "REVIEW_REQUEST")


def test_only_current_head_codex_evidence_is_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current = _review(
        "APPROVED",
        """<!-- agent-review-evidence
{"outcome":"clean","findings":[]}
-->""",
    )[0]
    stale = {**current, "commit_id": "b" * 40}
    requests: list[object] = []
    clock = iter((0.0, 1.0))

    assert find_verdict([stale], _HEAD, _REVIEWER) is None
    monkeypatch.setattr(request_codex_review, "_fetch_reviews", lambda *_args: [stale])
    monkeypatch.setattr(request_codex_review, "run_gh", requests.append, raising=False)
    assert (
        poll_for_verdict(
            "owner/repo",
            "14",
            _HEAD,
            timeout_seconds=1,
            poll_seconds=1,
            sleep=lambda _seconds: None,
            monotonic=lambda: next(clock),
        )
        is None
    )
    assert requests == []


def test_main_publishes_the_full_validated_codex_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verdict = {
        "outcome": "rework",
        "findings": [
            {
                "severity": "should-fix",
                "confidence": "high",
                "summary": "The fallback must publish every finding.",
            }
        ],
    }
    published: list[str] = []
    monkeypatch.setattr(request_codex_review, "poll_for_verdict", lambda *_args, **_kwargs: verdict)
    monkeypatch.setattr(request_codex_review, "publish_step_output", published.append)

    request_codex_review.main(["--repo", "owner/repo", "--pr", "14", "--head-sha", _HEAD])

    assert published == [f"payload={json.dumps(verdict, separators=(',', ':'))}"]


def test_main_publishes_an_empty_payload_when_codex_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published: list[str] = []
    monkeypatch.setattr(request_codex_review, "poll_for_verdict", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(request_codex_review, "publish_step_output", published.append)

    request_codex_review.main(["--repo", "owner/repo", "--pr", "14", "--head-sha", _HEAD])

    assert published == ["payload="]
