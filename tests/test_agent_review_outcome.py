"""Behavioural contract for structured agent-review evidence."""

from __future__ import annotations

import json

import pytest

from scripts import check_agent_review_outcome


def _classify(payload: dict[str, object], capsys: pytest.CaptureFixture[str]) -> str:
    check_agent_review_outcome.main([json.dumps(payload), "--classify"])
    return capsys.readouterr().out


def test_blocking_without_findings_is_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify({"outcome": "blocking"}, capsys)


def test_rework_without_findings_is_invalid(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify({"outcome": "rework"}, capsys)


def test_rework_cannot_hide_a_blocking_finding(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify(
        {
            "outcome": "rework",
            "findings": [
                {
                    "severity": "blocking",
                    "confidence": "high",
                    "summary": "A blocking finding must block the required check.",
                }
            ],
        },
        capsys,
    )


def test_blocking_requires_a_blocking_finding(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify(
        {
            "outcome": "blocking",
            "findings": [
                {
                    "severity": "should-fix",
                    "confidence": "high",
                    "summary": "Lower-severity feedback cannot request changes.",
                }
            ],
        },
        capsys,
    )


def test_clean_requires_no_findings(capsys: pytest.CaptureFixture[str]) -> None:
    assert "valid=false" in _classify(
        {
            "outcome": "clean",
            "findings": [
                {
                    "severity": "should-fix",
                    "confidence": "high",
                    "summary": "A clean review cannot carry a finding.",
                }
            ],
        },
        capsys,
    )


def test_valid_blocking_finding_is_reported_with_head_sha(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    check_agent_review_outcome.main(
        [
            json.dumps(
                {
                    "outcome": "blocking",
                    "findings": [
                        {
                            "severity": "blocking",
                            "confidence": "high",
                            "summary": "The required review result has no inspectable finding.",
                        }
                    ],
                }
            ),
            "--publish-summary",
            "--reviewed-head-sha",
            "a" * 40,
        ]
    )

    assert "a" * 40 in summary.read_text(encoding="utf-8")
    assert "BLOCKING" in summary.read_text(encoding="utf-8")
    assert "The required review result has no inspectable finding." in summary.read_text(
        encoding="utf-8"
    )


def test_fallback_findings_are_posted_to_the_pr(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return "[[]]"
        return "{}"

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps(
                {
                    "outcome": "rework",
                    "findings": [
                        {
                            "severity": "should-fix",
                            "confidence": "high",
                            "summary": "A real edge case in the drift-gate fix.",
                        }
                    ],
                }
            ),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            "a" * 40,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 2
    list_call, post_call = calls
    assert "repos/owner/repo/issues/42/comments" in list_call
    assert "--method" in post_call and "POST" in post_call
    body_arg = post_call[post_call.index("-f") + 1]
    assert body_arg.startswith("body=")
    assert "a" * 40 in body_arg
    assert "NON-BLOCKING" in body_arg
    assert "A real edge case in the drift-gate fix." in body_arg


def test_clean_outcome_still_posts_a_no_findings_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return "[[]]"
        return "{}"

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps({"outcome": "clean", "findings": []}),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            "e" * 40,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 2
    post_call = calls[1]
    assert "--method" in post_call and "POST" in post_call
    body_arg = post_call[post_call.index("-f") + 1]
    assert "No findings." in body_arg


def test_rerun_on_the_same_head_does_not_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    sha = "b" * 40
    existing_body = f"<!-- agent-review-claude-fallback -->\nReviewed head SHA: `{sha}`\n"

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return json.dumps([[{"id": 1, "body": existing_body}]])
        raise AssertionError("must not write to the PR when the reviewed head is unchanged")

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps({"outcome": "clean", "findings": []}),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            sha,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 1


def test_a_new_head_updates_the_existing_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    old_sha = "c" * 40
    new_sha = "d" * 40
    existing_body = f"<!-- agent-review-claude-fallback -->\nReviewed head SHA: `{old_sha}`\n"

    def fake_run_gh(args: list[str]) -> str:
        calls.append(args)
        if "--paginate" in args:
            return json.dumps([[{"id": 7, "body": existing_body}]])
        return "{}"

    monkeypatch.setattr(check_agent_review_outcome, "run_gh", fake_run_gh, raising=False)

    check_agent_review_outcome.main(
        [
            json.dumps({"outcome": "clean", "findings": []}),
            "--publish-pr-comment",
            "--reviewed-head-sha",
            new_sha,
            "--repo",
            "owner/repo",
            "--pr",
            "42",
        ]
    )

    assert len(calls) == 2
    patch_call = calls[1]
    assert "--method" in patch_call and "PATCH" in patch_call
    assert "repos/owner/repo/issues/comments/7" in patch_call
    body_arg = patch_call[patch_call.index("-f") + 1]
    assert new_sha in body_arg
