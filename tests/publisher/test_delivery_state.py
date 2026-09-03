"""Tests for the delivery turn-boundary decision table.

The end of an agent turn is the one step of the delivery flow that was still
governed by prose ("stay active through the review/fix loop") rather than a
script with an exit code. `delivery_state.decide()` is that script's decision;
these tests are its RED set (issue #56).
"""

from __future__ import annotations

from scripts.delivery_state import (
    MAX_CONSECUTIVE_BLOCKS,
    BudgetRecord,
    apply_budget,
    decide,
    fingerprint,
)

_HEAD = "a54549ac1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e"  # pragma: allowlist secret
_OLDER_HEAD = "3312ff63a4b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5"  # pragma: allowlist secret
_BRANCH = "issue-56-bug-keep-delivery-active"


class TestDeliveryBlocker:
    def test_non_delivery_branch_is_never_blocked(self) -> None:
        decision = decide("main", _HEAD, ci_stamp=None, gate_stamp=None)

        assert decision.action == "allow"

    def test_missing_ci_stamp_blocks_naming_ci_check(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=None, gate_stamp=None)

        assert decision.action == "block"
        assert "ci_check.py" in decision.next_action

    def test_stale_ci_stamp_blocks_naming_ci_check(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_OLDER_HEAD, gate_stamp=None)

        assert decision.action == "block"
        assert "ci_check.py" in decision.next_action

    def test_fresh_ci_stamp_with_no_gate_record_blocks_naming_open_pr(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=None)

        assert decision.action == "block"
        assert "open_pr.py" in decision.next_action

    def test_gate_record_on_an_older_head_blocks_naming_the_review_loop(self) -> None:
        decision = decide(
            _BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_OLDER_HEAD, "ready-for-human")
        )

        assert decision.action == "block"
        assert "review_gate.py" in decision.next_action

    def test_fix_blocking_verdict_blocks(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "fix-blocking"))

        assert decision.action == "block"

    def test_review_pending_verdict_blocks(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "review-pending"))

        assert decision.action == "block"

    def test_gate_capture_failure_record_blocks(self) -> None:
        """`review_gate.py`'s own `gate-error` marker is progress, not terminal —
        it needs no special-casing: it simply is not in `TERMINAL_VERDICTS`."""
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "gate-error"))

        assert decision.action == "block"

    def test_ready_for_human_on_the_current_head_is_not_blocked(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "ready-for-human"))

        assert decision.action == "allow"

    def test_escalate_on_the_current_head_is_not_blocked(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "escalate"))

        assert decision.action == "allow"

    def test_dirty_worktree_blocks_even_on_a_terminal_verdict(self) -> None:
        """`HEAD` and both stamps are silent about changes made *after* they were
        written — a dirty worktree means the current state was never checked or
        reviewed, so it must not read as terminal (agent-review finding on #56)."""
        decision = decide(
            _BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "ready-for-human"), dirty=True
        )

        assert decision.action == "block"
        assert "uncommitted" in decision.reason


class TestBlockBudget:
    def test_an_unchanged_fingerprint_exhausts_the_budget_and_escalates(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=None, gate_stamp=None)
        fp = fingerprint(_BRANCH, _HEAD, None, None)
        record: BudgetRecord | None = None

        for _ in range(MAX_CONSECUTIVE_BLOCKS):
            result, record = apply_budget(decision, fp, record)
            assert result.action == "block"

        result, record = apply_budget(decision, fp, record)

        assert result.action == "escalate"
        assert record is not None
        assert record.consecutive_blocks == MAX_CONSECUTIVE_BLOCKS + 1

    def test_a_changed_fingerprint_resets_the_counter(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=None, gate_stamp=None)
        stale_fp = fingerprint(_BRANCH, _HEAD, None, None)
        advanced_fp = fingerprint(_BRANCH, _HEAD, _HEAD, None)
        record: BudgetRecord | None = None
        for _ in range(MAX_CONSECUTIVE_BLOCKS):
            _, record = apply_budget(decision, stale_fp, record)

        result, record = apply_budget(decision, advanced_fp, record)

        assert result.action == "block"
        assert record is not None
        assert record.consecutive_blocks == 1

    def test_an_allow_decision_clears_budget_tracking(self) -> None:
        decision = decide(_BRANCH, _HEAD, ci_stamp=_HEAD, gate_stamp=(_HEAD, "ready-for-human"))
        previous = BudgetRecord(fingerprint="anything", consecutive_blocks=MAX_CONSECUTIVE_BLOCKS)

        result, record = apply_budget(decision, "anything", previous)

        assert result.action == "allow"
        assert record is None
