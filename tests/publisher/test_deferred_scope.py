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

import json
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


def test_unparseable_entry_inside_the_block_is_rejected() -> None:
    # Codex finding on PR #66: the old check only grepped the block for
    # `tracked in #N` occurrences, so an added bullet with no such suffix was
    # silently ignored rather than rejected — letting an arbitrary entry sit
    # next to one legitimate tracked entry inside a block the contract calls
    # gate-verified.
    pr_body = (
        f"{open_pr.DEFERRED_SCOPE_BEGIN}\n## Deferred scope\n\n"
        "- an entry with no tracker suffix at all\n"
        f"{open_pr.DEFERRED_SCOPE_END}"
    )
    issue_body = _OUT_OF_SCOPE_TRACKED

    mismatch = verify_pr_link.deferred_scope_mismatch("issue-59-x", pr_body, issue_body)

    assert mismatch != []


def test_closed_tracker_referenced_in_the_pr_body_is_unsound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Codex should-fix on PR #66: a tracker closed after the block was
    # generated must not keep downgrading a finding merely because its number
    # still sits in a `deferred:` bullet in the source issue's text.
    pr_body = _pr_body_referencing(61)
    issue_body = _OUT_OF_SCOPE_TRACKED
    monkeypatch.setattr(open_pr, "_fetch_issue", lambda n: _issue(n, state="CLOSED"))

    unsound = verify_pr_link._unsound_with_liveness("issue-59-x", pr_body, issue_body)

    assert 61 in unsound


def test_open_tracker_referenced_in_the_pr_body_stays_sound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pr_body = _pr_body_referencing(61)
    issue_body = _OUT_OF_SCOPE_TRACKED
    monkeypatch.setattr(open_pr, "_fetch_issue", lambda n: _issue(n, state="OPEN"))

    unsound = verify_pr_link._unsound_with_liveness("issue-59-x", pr_body, issue_body)

    assert unsound == []


def test_block_present_but_unparseable_as_bullets_is_rejected() -> None:
    # Claude finding on PR #66 (fresh review after the round-1 fixes): a
    # sentinel-delimited block whose content fails to parse as a top-level
    # bullet list at all (wrong/missing heading, or prose instead of a `- `
    # list) made `_block_bullets` return [] the same way "sentinels absent"
    # does — so `deferred_scope_mismatch` took the early-return "nothing to
    # check" branch and called it sound. `render_deferred_scope_section`
    # never renders sentinels around an empty block (it omits them entirely
    # when there is nothing to export), so this shape can only arise from
    # hand-editing/corruption after generation — exactly the case that must
    # be flagged, not waved through.
    pr_body = (
        f"{open_pr.DEFERRED_SCOPE_BEGIN}\n"
        "just some prose, not a bullet list under the expected heading\n"
        f"{open_pr.DEFERRED_SCOPE_END}"
    )
    issue_body = _OUT_OF_SCOPE_TRACKED

    mismatch = verify_pr_link.deferred_scope_mismatch("issue-59-x", pr_body, issue_body)

    assert mismatch != []


# ---------------------------------------------------------------------------
# verify_pr_link: the source-issue read is conditional on the block (issue #68)
# ---------------------------------------------------------------------------

# The two records of the `## Evidence` capture on issue #68, rebuilt here
# rather than replayed raw. Captured working-tree-only (git-ignored) with
# `python .agent-process/scripts/capture_external_fixture.py github
#  "repos/ekolvah/agent-process-distribution/issues?state=all&labels=bug&per_page=10"
#  evidence/issue-68/issues-state-all-bug.json --confirm-repository-safe`.
# REST reports `open`/`closed`, whereas the production route
# `gh issue view <N> --json body,state` reports `OPEN`/`CLOSED` — and the
# latter is the string `fetch_issue_body` actually compares, so committing the
# REST payload would pin a wire shape this code path never sees.
_CAPTURED_OPEN = 68  # preserve record: still fetched and still verified
_CAPTURED_CLOSED = 67  # change record: must stop hard-failing a no-block PR


class _IssueReads:
    """Recording stub for `check_orphan_scope.fetch_issue_body` — the one `gh`
    seam issue #68 is about. Reproduces the real contract (a `RuntimeError` for
    any non-OPEN state) so "was the issue read at all?" is asserted, not
    assumed. Named explicitly rather than patching `verify_pr_link.subprocess`:
    the module does `import subprocess`, so there is no per-module seam there —
    patching the stdlib module would swallow every other caller too, and
    patching the attribute would not reach `fetch_issue_body` at all."""

    def __init__(self, *, state: str, body: str) -> None:
        self.state = state
        self.body = body
        self.calls: list[int] = []

    def __call__(self, number: int) -> str:
        self.calls.append(number)
        if self.state != "OPEN":
            raise RuntimeError(f"issue #{number} is not OPEN (state={self.state})")
        return self.body


def _stub_gh_seams(
    monkeypatch: pytest.MonkeyPatch,
    *,
    issue_state: str,
    issue_body: str,
    pr_body: str,
) -> _IssueReads:
    """Stub every named `gh` boundary `verify_pr_link.main` can reach."""
    reads = _IssueReads(state=issue_state, body=issue_body)
    monkeypatch.setattr(check_orphan_scope, "fetch_issue_body", reads)
    monkeypatch.setattr(verify_pr_link, "_pr_body", lambda pr: pr_body)
    monkeypatch.setattr(
        verify_pr_link,
        "_refs_json",
        lambda pr: json.dumps({"closingIssuesReferences": [{"number": 1}]}),
    )
    monkeypatch.setattr(
        open_pr,
        "_fetch_issue",
        lambda n: pytest.fail(f"tracker liveness must not be reached here (issue #{n})"),
    )
    return reads


def _run_main(branch: str) -> int:
    """`verify_pr_link.main` exit code — 0 when it returns without exiting."""
    try:
        verify_pr_link.main(["--branch", branch, "--pr", "7"])
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


@pytest.mark.parametrize(
    ("number", "state", "pr_body", "expected_exit", "expected_reads", "expected_message"),
    [
        pytest.param(
            _CAPTURED_CLOSED,
            "CLOSED",
            "## Summary\n\nnothing here\n",
            0,
            [],
            "ok: PR link check passed",
            id="change-67-closed-no-block",
        ),
        pytest.param(
            _CAPTURED_OPEN,
            "OPEN",
            _pr_body_referencing(99),
            1,
            [_CAPTURED_OPEN],
            "is not gate-verified sound",
            id="preserve-68-open-unbacked-tracker",
        ),
    ],
)
def test_paired_no_block_passes_while_open_record_still_verifies(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    number: int,
    state: str,
    pr_body: str,
    expected_exit: int,
    expected_reads: list[int],
    expected_message: str,
) -> None:
    # The paired test of issue #68's `## Evidence`: one pipeline run per
    # captured record. The closed record must stop hard-failing a PR that
    # carries nothing for this check to verify, while the open record keeps
    # being fetched and keeps redding an unbacked tracker.
    reads = _stub_gh_seams(
        monkeypatch, issue_state=state, issue_body=_OUT_OF_SCOPE_TRACKED, pr_body=pr_body
    )

    exit_code = _run_main(f"issue-{number}-x")

    captured = capsys.readouterr()
    assert exit_code == expected_exit
    assert reads.calls == expected_reads
    assert expected_message in captured.out + captured.err


def test_closed_source_issue_with_a_real_block_still_fails_visibly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The other half of the captured change record, and the guard that stops
    # the fix from passing by deleting the check: a not-OPEN source issue is
    # still a hard, visible failure (§IV) once there IS a block to verify.
    reads = _stub_gh_seams(
        monkeypatch,
        issue_state="CLOSED",
        issue_body="",
        pr_body=_pr_body_referencing(61),
    )

    with pytest.raises(SystemExit) as excinfo:
        verify_pr_link._unsound_deferred_trackers(f"issue-{_CAPTURED_CLOSED}-x", "7")

    assert excinfo.value.code == 2
    assert reads.calls == [_CAPTURED_CLOSED]
    assert (
        f"could not read issue #{_CAPTURED_CLOSED} to verify deferred-scope soundness"
        in capsys.readouterr().err
    )


def test_malformed_block_still_reads_the_source_issue(monkeypatch: pytest.MonkeyPatch) -> None:
    # The short-circuit keys on "sentinels absent" (`_block_bullets` → None),
    # never on "no parsed bullets" — otherwise it would undo PR #66's
    # malformed-block fix, which reports `[0]` for exactly this shape.
    pr_body = (
        f"{open_pr.DEFERRED_SCOPE_BEGIN}\n"
        "just some prose, not a bullet list under the expected heading\n"
        f"{open_pr.DEFERRED_SCOPE_END}"
    )
    reads = _stub_gh_seams(
        monkeypatch, issue_state="OPEN", issue_body=_OUT_OF_SCOPE_TRACKED, pr_body=pr_body
    )

    unsound = verify_pr_link._unsound_deferred_trackers("issue-59-x", "7")

    assert reads.calls == [59]
    assert 0 in unsound


def test_non_issue_branch_makes_no_gh_call(monkeypatch: pytest.MonkeyPatch) -> None:
    # The docstring promise the reorder must not break: "No `gh` call at all
    # for a non-issue branch … the fetches are skipped, not just their result
    # discarded." Moving `_pr_body` up must stay BELOW the branch guard.
    def _forbidden(*args: object, **kwargs: object) -> object:
        pytest.fail("a non-issue branch must make no `gh` call")

    monkeypatch.setattr(check_orphan_scope, "fetch_issue_body", _forbidden)
    monkeypatch.setattr(verify_pr_link, "_pr_body", _forbidden)
    monkeypatch.setattr(verify_pr_link, "_refs_json", _forbidden)

    assert verify_pr_link._unsound_deferred_trackers("main", "7") == []
