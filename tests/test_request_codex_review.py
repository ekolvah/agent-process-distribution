"""The manual Codex carrier translates GitHub-native review records."""

from __future__ import annotations

import subprocess
import sys

import pytest

from scripts import request_codex_review
from scripts.request_codex_review import (
    find_clean_reaction,
    find_verdict,
    poll_for_verdict,
)

_HEAD = "a" * 40
_REVIEWER = "chatgpt-codex-connector[bot]"


def test_request_command_posts_the_exact_codex_trigger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(request_codex_review, "run_gh", lambda args: calls.append(args) or "")

    request_codex_review.main(["--request", "37"])

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


def _request(*, created_at: str = "2026-08-24T08:32:00Z") -> dict[str, object]:
    return {
        "id": 99,
        "user": {"login": "author"},
        "body": "@codex review",
        "created_at": created_at,
    }


def _clean_comment(
    *,
    author: str = _REVIEWER,
    body: str | None = None,
    created_at: str = "2026-08-24T08:33:00Z",
) -> dict[str, object]:
    return {
        "user": {"login": author},
        "created_at": created_at,
        "body": body
        or "Codex Review: Didn't find any major issues. :tada:\n\n"
        f"**Reviewed commit:** `{_HEAD[:10]}`",
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
    request = _request()
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


def test_sha_bound_clean_comment_is_clean_evidence() -> None:
    assert request_codex_review.find_clean_comment(
        [_request(), _clean_comment()],
        author_login="author",
        head_sha=_HEAD,
        head_observed_at="2026-08-24T08:31:00Z",
        reviewer=_REVIEWER,
    ) == {"outcome": "clean", "findings": []}


@pytest.mark.parametrize(
    "comment",
    [
        _clean_comment(author="another-bot[bot]"),
        _clean_comment(body="Codex Review: clean\n\n**Reviewed commit:** `aaaaaaaaaa`"),
        _clean_comment(
            body="Codex Review: Didn't find any major issues. :tada:\n\n**Reviewed commit:** `not-a-sha`"
        ),
        _clean_comment(
            body=(
                "Codex Review: Didn't find any major issues. :tada:\n\n"
                "**Reviewed commit:** `aaaaaaaaaa`\n"
                "**Reviewed commit:** `aaaaaaaaaa`"
            )
        ),
        _clean_comment(
            body="Codex Review: Didn't find any major issues. :tada:\n\n**Reviewed commit:** `bbbbbbbbbb`"
        ),
        _clean_comment(created_at="2026-08-24T08:30:00Z"),
    ],
)
def test_clean_comment_rejects_wrong_author_marker_time_and_head(
    comment: dict[str, object],
) -> None:
    assert (
        request_codex_review.find_clean_comment(
            [_request(), comment],
            author_login="author",
            head_sha=_HEAD,
            head_observed_at="2026-08-24T08:31:00Z",
            reviewer=_REVIEWER,
        )
        is None
    )


def test_latest_current_head_evidence_wins_across_comment_and_native_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    earlier_p1 = {
        **_review("COMMENTED"),
        "submitted_at": "2026-08-24T08:33:00Z",
    }
    monkeypatch.setattr(request_codex_review, "_fetch_reviews", lambda *_args: [earlier_p1])
    monkeypatch.setattr(
        request_codex_review,
        "_fetch_review_comments",
        lambda *_args: [_comment("P1 later native finding")],
    )
    monkeypatch.setattr(
        request_codex_review,
        "_fetch_request_comments",
        lambda *_args: [_request(), _clean_comment(created_at="2026-08-24T08:34:00Z")],
    )
    monkeypatch.setattr(request_codex_review, "_clean_reaction_context", lambda *_args: "author")
    monkeypatch.setattr(request_codex_review, "_fetch_reactions", lambda *_args: [])

    verdict = poll_for_verdict(
        "owner/repo",
        "14",
        _HEAD,
        head_observed_at="2026-08-24T08:31:00Z",
        timeout_seconds=0,
    )

    assert verdict == {"outcome": "clean", "findings": []}

    later_p1 = {**earlier_p1, "submitted_at": "2026-08-24T08:35:00Z"}
    monkeypatch.setattr(request_codex_review, "_fetch_reviews", lambda *_args: [later_p1])

    verdict = poll_for_verdict(
        "owner/repo",
        "14",
        _HEAD,
        head_observed_at="2026-08-24T08:31:00Z",
        timeout_seconds=0,
    )

    assert verdict is not None
    assert verdict["outcome"] == "blocking"


def test_poll_checks_supported_clean_comment_before_declaring_current_head_evidence_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        request_codex_review, "_fetch_reviews", lambda *_args: [_review("COMMENTED")]
    )
    monkeypatch.setattr(request_codex_review, "_fetch_review_comments", lambda *_args: [])
    monkeypatch.setattr(
        request_codex_review,
        "_fetch_request_comments",
        lambda *_args: [_request(), _clean_comment()],
    )
    monkeypatch.setattr(request_codex_review, "_clean_reaction_context", lambda *_args: "author")
    monkeypatch.setattr(request_codex_review, "_fetch_reactions", lambda *_args: [])

    assert poll_for_verdict(
        "owner/repo",
        "14",
        _HEAD,
        head_observed_at="2026-08-24T08:31:00Z",
        timeout_seconds=0,
    ) == {"outcome": "clean", "findings": []}


def test_poll_stops_when_a_current_head_review_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        request_codex_review, "_fetch_reviews", lambda *_args: [_review("COMMENTED")]
    )
    monkeypatch.setattr(request_codex_review, "_fetch_review_comments", lambda *_args: [])
    monkeypatch.setattr(request_codex_review, "_clean_reaction_context", lambda *_args: "author")
    monkeypatch.setattr(request_codex_review, "_fetch_request_comments", lambda *_args: [])

    assert (
        poll_for_verdict(
            "owner/repo",
            "14",
            _HEAD,
            head_observed_at="2026-08-24T08:31:00Z",
            timeout_seconds=0,
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
    monkeypatch.setattr(request_codex_review, "_clean_reaction_context", lambda *_args: "author")
    monkeypatch.setattr(request_codex_review, "_fetch_request_comments", lambda *_args: [])

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
    assert "Request or read the standard GitHub review" in result.stdout
