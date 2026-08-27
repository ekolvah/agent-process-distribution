"""The manual Codex carrier translates GitHub-native review records."""

from __future__ import annotations

import subprocess
import sys

import pytest

from scripts import request_codex_review
from scripts.request_codex_review import find_clean_reaction, find_verdict, poll_for_verdict

_HEAD = "a" * 40
_REVIEWER = "chatgpt-codex-connector[bot]"


def test_request_command_posts_the_exact_codex_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(request_codex_review, "run_gh", lambda args: calls.append(args) or "")

    request_codex_review.request_review("37")

    assert calls == [["pr", "comment", "37", "--body", "@codex review"]]


def test_request_command_surfaces_a_github_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_args: list[str]) -> str:
        raise RuntimeError("gh pr comment failed: permission denied")

    monkeypatch.setattr(request_codex_review, "run_gh", fail)

    with pytest.raises(RuntimeError, match="permission denied"):
        request_codex_review.request_review("37")


def _review(state: str) -> dict[str, object]:
    return {
        "id": 42,
        "user": {"login": _REVIEWER},
        "commit_id": _HEAD,
        "state": state,
        "body": "### Codex Review",
    }


def _comment(body: str) -> dict[str, object]:
    return {
        "pull_request_review_id": 42,
        "body": body,
        "user": {"login": _REVIEWER},
    }


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


def test_codex_comment_without_a_priority_is_invalid_evidence() -> None:
    assert find_verdict([_review("COMMENTED")], [_comment("Fix this")], _HEAD, _REVIEWER) is None


def test_human_reply_does_not_become_a_codex_finding() -> None:
    reply = {
        **_comment("P1 is not applicable here"),
        "user": {"login": "author"},
        "in_reply_to_id": 100,
    }
    verdict = find_verdict(
        [_review("COMMENTED")],
        [_comment("**![P2 Badge](https://example.test/p2) Update guidance"), reply],
        _HEAD,
        _REVIEWER,
    )

    assert verdict is not None
    assert verdict["outcome"] == "rework"
    assert len(verdict["findings"]) == 1


def test_changes_requested_requires_a_blocking_codex_finding() -> None:
    assert (
        find_verdict(
            [_review("CHANGES_REQUESTED")],
            [_comment("**![P2 Badge](https://example.test/p2) Update guidance")],
            _HEAD,
            _REVIEWER,
        )
        is None
    )


def test_only_current_head_codex_review_is_accepted() -> None:
    stale = {**_review("APPROVED"), "commit_id": "b" * 40}

    assert find_verdict([stale], [], _HEAD, _REVIEWER) is None


def test_latest_current_head_review_overrides_an_older_clean_verdict() -> None:
    assert (
        find_verdict(
            [_review("APPROVED"), _review("COMMENTED")],
            [],
            _HEAD,
            _REVIEWER,
        )
        is None
    )


def test_clean_reaction_must_follow_the_github_observed_head_transition() -> None:
    request = {
        "id": 99,
        "user": {"login": "author"},
        "body": "@codex review",
        "created_at": "2026-08-24T08:32:00Z",
    }
    reactions = {99: [{"content": "+1", "user": {"login": _REVIEWER}}]}

    assert find_clean_reaction(
        [request],
        reactions,
        author_login="author",
        head_observed_at="2026-08-24T08:31:00Z",
        reviewer=_REVIEWER,
    ) == {"outcome": "clean", "findings": []}
    assert (
        find_clean_reaction(
            [request],
            reactions,
            author_login="author",
            head_observed_at="2026-08-24T08:33:00Z",
            reviewer=_REVIEWER,
        )
        is None
    )


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
            head_observed_at="2026-08-24T08:31:00Z",
            timeout_seconds=60,
            poll_seconds=1,
            sleep=lambda _seconds: None,
            monotonic=lambda: next(clock),
        )
        is None
    )


def test_poll_accepts_valid_codex_evidence_without_a_policy_path_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        request_codex_review, "_fetch_reviews", lambda *_args: [_review("COMMENTED")]
    )
    monkeypatch.setattr(
        request_codex_review,
        "_fetch_review_comments",
        lambda *_args: [_comment("P1 review policy defect")],
    )

    verdict = poll_for_verdict(
        "owner/repo",
        "14",
        _HEAD,
        head_observed_at="2026-08-24T08:31:00Z",
        timeout_seconds=0,
    )

    assert verdict is not None
    assert verdict["outcome"] == "blocking"


def test_module_entry_point_runs_the_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "scripts.request_codex_review", "--help"],
        capture_output=True,
        check=False,
        encoding="utf-8",
        text=True,
    )

    assert result.returncode == 0
    assert "Read the standard GitHub review" in result.stdout
