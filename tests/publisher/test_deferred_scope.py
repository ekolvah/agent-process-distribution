"""A tracked, deliberately deferred Out-of-scope bullet downgrades a matching
`agent-review` finding instead of being re-reported as BLOCKING every round.

Reclassified publisher-only (issue #64): the four scripts under test
(`check_orphan_scope.py`, `open_pr.py`, `update_pr_body.py`,
`verify_pr_link.py`) are byte-static across template renders, so this suite
owns their new behaviour directly rather than through a rendered consumer
copy (`tests/publisher/test_hooks.py` is the precedent for that split).

Only the boundary — `open_pr._fetch_issue`, the module's one `gh` seam for
issue reads — is monkeypatched; every parsing/rendering function under test
is pure and exercised directly (principles.md §II: no mocks of internal
logic).
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts import check_orphan_scope, open_pr, update_pr_body, verify_pr_link

_OUT_OF_SCOPE_TRACKED = """\
## Out of scope

- deferred: Findings 2 and 3 against the recovered code — carved into #61.
- Adding a `--remove-retired` flag (wontfix, YAGNI here).

## Architect review
"""


def _issue(
    number: int,
    *,
    title: str = "Recover the adoption CLI's owner checks",
    state: str = "OPEN",
    body: str = "",
) -> dict[str, Any]:
    return {"number": number, "title": title, "state": state, "body": body}


# ---------------------------------------------------------------------------
# check_orphan_scope: opt-in selection of deferred bullets
# ---------------------------------------------------------------------------


def test_deferred_bullet_with_open_tracker_is_exported() -> None:
    bullets = check_orphan_scope.deferred_scope_bullets(_OUT_OF_SCOPE_TRACKED)

    assert len(bullets) == 1
    assert "carved into #61" in bullets[0]
    assert check_orphan_scope.deferred_scope_trackers(bullets[0]) == [61]


def test_bullet_with_an_incidental_issue_number_is_not_exported() -> None:
    # No `deferred:` prefix: citing #61 in passing must not, by itself, license
    # a downgrade (issue #64 finding B3) — this is deliberately NOT the
    # complement of `find_orphan_scope_reminders`.
    body = """\
## Out of scope

- Findings 2 and 3 against the recovered code — carved into #61.
"""
    assert check_orphan_scope.deferred_scope_bullets(body) == []


def test_rejected_bullet_is_not_exported() -> None:
    body = """\
## Out of scope

- deferred: revisit the flag from #61 (wontfix, YAGNI here).
"""
    assert check_orphan_scope.deferred_scope_bullets(body) == []


# ---------------------------------------------------------------------------
# open_pr: rendering a matchable, sentinel-delimited section
# ---------------------------------------------------------------------------


def test_entry_carries_tracker_title_and_bounded_acceptance_bullets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker_body = """\
## Acceptance criteria

1. Preflight validates managed fragments before writing.
2. An update removes owned paths no longer present.
3. A regression test locks the removal path.
4. A fifth criterion that must be truncated away.
"""
    issues = {
        59: _issue(59, body=_OUT_OF_SCOPE_TRACKED),
        61: _issue(61, title="Harden adoption preflight and removal", body=tracker_body),
    }
    monkeypatch.setattr(open_pr, "_fetch_issue", lambda n: issues.get(n))

    section = open_pr.render_deferred_scope_section(59)

    assert section.count(open_pr.DEFERRED_SCOPE_BEGIN) == 1
    assert section.count(open_pr.DEFERRED_SCOPE_END) == 1
    assert "#61" in section
    assert "Harden adoption preflight and removal" in section
    assert "Preflight validates managed fragments" in section
    assert "An update removes owned paths" in section
    assert "A regression test locks the removal path" in section
    assert "fifth criterion" not in section  # bounded, not the whole list


def test_generic_tracker_title_still_yields_a_matchable_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tracker_body = "## Acceptance criteria\n\n1. Validate managed fragments during preflight.\n"
    issues = {
        59: _issue(59, body=_OUT_OF_SCOPE_TRACKED),
        61: _issue(61, title="Follow-up", body=tracker_body),
    }
    monkeypatch.setattr(open_pr, "_fetch_issue", lambda n: issues.get(n))

    section = open_pr.render_deferred_scope_section(59)

    # A generic title alone would be unmatchable; the acceptance bullet is
    # what a reviewer can actually match its own finding against.
    assert "Validate managed fragments during preflight" in section


def test_closed_tracking_issue_is_omitted_and_reported(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    issues = {
        59: _issue(59, body=_OUT_OF_SCOPE_TRACKED),
        61: _issue(61, state="CLOSED", body="## Acceptance criteria\n\n1. Done.\n"),
    }
    monkeypatch.setattr(open_pr, "_fetch_issue", lambda n: issues.get(n))

    section = open_pr.render_deferred_scope_section(59)

    assert section == ""
    assert "#61" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# open_pr: idempotent, sentinel-scoped replacement
# ---------------------------------------------------------------------------


def test_regeneration_between_sentinels_is_idempotent() -> None:
    rendered = f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n- entry\n{open_pr.DEFERRED_SCOPE_END}"
    body = "Summary prose.\n\nCloses #59\n"

    once = open_pr.ensure_deferred_scope(body, rendered)
    twice = open_pr.ensure_deferred_scope(once, rendered)

    assert once == twice
    assert once.count(open_pr.DEFERRED_SCOPE_BEGIN) == 1
    assert once.count(open_pr.DEFERRED_SCOPE_END) == 1
    assert "Summary prose." in once
    assert "Closes #59" in once


def test_regeneration_preserves_author_prose_outside_the_sentinels() -> None:
    existing = (
        "Summary prose.\n\n"
        f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n- stale entry\n"
        f"{open_pr.DEFERRED_SCOPE_END}\n\n"
        "A maintainer note the author wrote below the block."
    )
    rendered = f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n- fresh entry\n{open_pr.DEFERRED_SCOPE_END}"

    updated = open_pr.ensure_deferred_scope(existing, rendered)

    assert "stale entry" not in updated
    assert "fresh entry" in updated
    assert "A maintainer note the author wrote below the block." in updated
    assert "Summary prose." in updated


# ---------------------------------------------------------------------------
# open_pr / update_pr_body: degradation on an unreachable source issue
# ---------------------------------------------------------------------------


def test_unreachable_issue_preserves_the_existing_block_and_warns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(open_pr, "_fetch_issue", lambda _n: None)
    existing_block = (
        f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n- kept entry\n"
        f"{open_pr.DEFERRED_SCOPE_END}"
    )
    current_body = f"Summary.\n\n{existing_block}\n"

    rendered = open_pr.deferred_scope_for_body(current_body, 59)

    assert rendered == existing_block
    assert "unreachable" in capsys.readouterr().err.lower() or "59" in capsys.readouterr().err


def test_update_pr_body_keeps_the_block_and_normalized_body_stays_pure() -> None:
    rendered = f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n- entry\n{open_pr.DEFERRED_SCOPE_END}"
    body = "Report body.\n"

    first = update_pr_body.normalized_body(body, 59, rendered)
    second = update_pr_body.normalized_body(body, 59, rendered)

    assert first == second  # pure: no I/O, deterministic on identical inputs
    assert "Closes #59" in first
    assert rendered in first


# ---------------------------------------------------------------------------
# verify_pr_link: soundness, not equality
# ---------------------------------------------------------------------------


def _pr_body_referencing(*tracker_numbers: int) -> str:
    entries = "\n".join(f"- some finding (tracked in #{n}: some title)" for n in tracker_numbers)
    return f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n{entries}\n{open_pr.DEFERRED_SCOPE_END}"


def test_verify_pr_link_rejects_an_entry_not_backed_by_the_issue() -> None:
    pr_body = _pr_body_referencing(99)
    issue_body = _OUT_OF_SCOPE_TRACKED  # only backs #61, not #99

    assert verify_pr_link.deferred_scope_mismatch("issue-59-x", pr_body, issue_body) == [99]


def test_verify_pr_link_tolerates_a_retitled_or_reworded_issue() -> None:
    pr_body = _pr_body_referencing(61)
    reworded_issue_body = """\
## Out of scope

- deferred: the two remaining findings from the recovery work now live in #61,
  renamed and reworded since the PR body was generated.

## Architect review
"""

    assert verify_pr_link.deferred_scope_mismatch("issue-59-x", pr_body, reworded_issue_body) == []


def test_non_issue_branch_skips_the_section_check() -> None:
    pr_body = _pr_body_referencing(99)
    issue_body = _OUT_OF_SCOPE_TRACKED

    assert verify_pr_link.deferred_scope_mismatch("main", pr_body, issue_body) == []
