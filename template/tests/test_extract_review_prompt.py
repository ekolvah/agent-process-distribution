"""Unit tests for the review-contract extractor used by the reusable workflow."""

from __future__ import annotations

import pytest

from scripts.extract_review_prompt import extract_review_prompt


def test_extracts_the_code_review_rules_section() -> None:
    text = "# Agent guidance\n\n## Code Review Rules\n\n- Review carefully.\n\n## Other\n\nIgnored.\n"
    assert extract_review_prompt(text) == "- Review carefully."


@pytest.mark.parametrize(
    "text, marker",
    [
        ("# Agent guidance\n", "missing"),
        ("## Code Review Rules\n\n## Other\n", "empty"),
    ],
)
def test_missing_or_empty_contract_is_an_error(text: str, marker: str) -> None:
    with pytest.raises(ValueError, match=marker):
        extract_review_prompt(text)
