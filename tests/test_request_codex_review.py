"""Codex fallback must carry the same structured evidence as Claude."""

from __future__ import annotations

from scripts.request_codex_review import find_verdict

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
