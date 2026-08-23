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
    assert "The required review result has no inspectable finding." in summary.read_text(
        encoding="utf-8"
    )
