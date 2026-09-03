"""Whether an in-progress delivery has reached a terminal state — and the exact
next command when it has not.

Transport-neutral (the shape of `agent_policy.py` / `navigation_policy.py`): every
function here takes state as arguments and touches neither the filesystem nor a
subprocess. An adapter (Claude's `hooks.py stop`; a future Codex adapter, issue #75)
reads the local stamps and git state, then calls in.

Root cause this answers (issue #56): every other step of the delivery flow is
already a script with an exit code (`check_red.py`, `ci_check.py`, `open_pr.py`,
`review_gate.py`); the end of an agent turn was the one step still governed by
prose ("stay active through the review/fix loop") and got skipped. This module is
the decision a turn-boundary gate enforces instead of trusting that sentence.

Two facts decide everything: has CI verified the current HEAD
(`.ci_check_stamp`, written by `ci_check.py`), and what did the review/fix loop
last decide for the current HEAD (`.review_gate_stamp`, written by
`review_gate.py`, `<head> <verdict>`). Neither stamp is read here — the adapter
reads them and passes the values in, so this module stays a pure decision table.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

try:
    from scripts.new_branch import is_valid_branch_name
except ModuleNotFoundError:  # documented direct script entry point
    from new_branch import is_valid_branch_name

# Verdicts `review_gate.py` can report for the current HEAD that end the loop.
# Every other verdict — including a missing record, an older-head record, and
# `review_gate.py`'s own capture-failure marker (`gate-error`) — is progress.
TERMINAL_VERDICTS = frozenset({"ready-for-human", "escalate"})

# How many consecutive turn-ends may block on an *unchanged* delivery state
# before the gate lets the turn end anyway, with a visible marker (§IV), rather
# than trapping the session. A code constant, not role-catalogue data
# (`.agents/orchestration/roles.yaml`): `fixer.max_runs` / `review_gate.fixer_budget`
# count *role invocations* the catalogue already tracks per role; this counts
# *consecutive turn-ends*, has exactly one caller (the Stop adapter), and a
# catalogue read on every turn-end of every session would tax the hot path to
# serve a single, local constant. Chosen loosely: a real fix rarely needs more
# than a couple of turns per delivery step, and the budget only bounds the trap,
# it does not police delivery speed.
MAX_CONSECUTIVE_BLOCKS = 5

_CI_CHECK_NEXT = (
    "run `python .agent-process/scripts/ci_check.py` once in the foreground "
    "(raise the harness timeout — a full run can take minutes)"
)
_OPEN_PR_NEXT = "run `python .agent-process/scripts/open_pr.py`"
_REVIEW_LOOP_NEXT = (
    "run `python .agent-process/scripts/request_codex_review.py --request <PR>`, then "
    "`gh pr checks <PR> --watch`, then `python .agent-process/scripts/review_gate.py <PR>`"
)
_GATE_VERDICT_NEXT = (
    "follow the last `review_gate.py` verdict: `fix-blocking` → one fixer commit, push, "
    "re-run the gate; `review-pending` → wait once with `gh pr checks <PR> --watch`, "
    "then re-run the gate"
)
_UNREADABLE_STATE_NEXT = (
    "confirm the git working tree is sane (HEAD and branch resolve), then retry"
)


@dataclass(frozen=True)
class Decision:
    """What the turn-boundary gate should do.

    `action` is `"allow"` (terminal, or not a delivery branch — the turn ends
    silently), `"block"` (non-terminal, budget not exhausted — the turn must not
    end), or `"escalate"` (non-terminal, budget exhausted — the turn is allowed
    to end, but only with a visible marker naming what is incomplete).
    """

    action: str
    reason: str
    next_action: str


@dataclass(frozen=True)
class BudgetRecord:
    """Consecutive-block tracking for one delivery-state fingerprint."""

    fingerprint: str
    consecutive_blocks: int


def _decision(action: str, reason: str, next_action: str = "") -> Decision:
    return Decision(action=action, reason=reason, next_action=next_action)


def decide(
    branch: str,
    head: str,
    ci_stamp: str | None,
    gate_stamp: tuple[str, str] | None,
) -> Decision:
    """The raw decision table, before the block budget applies.

    `ci_stamp` is the content of `.ci_check_stamp` (a bare HEAD sha), or `None` if
    absent. `gate_stamp` is `(head, verdict)` from `.review_gate_stamp`, or `None`
    if absent. Both are compared against `head` as opaque strings — this module
    never resolves a ref itself.
    """
    if not is_valid_branch_name(branch):
        return _decision("allow", f"{branch!r} is not a delivery branch")
    if ci_stamp != head:
        return _decision("block", "no verified CI run recorded for HEAD", _CI_CHECK_NEXT)
    if gate_stamp is None:
        return _decision("block", "CI verified but no PR/review-gate record yet", _OPEN_PR_NEXT)
    gate_head, verdict = gate_stamp
    if gate_head != head:
        return _decision(
            "block", "the last review-gate verdict is for an older HEAD", _REVIEW_LOOP_NEXT
        )
    if verdict in TERMINAL_VERDICTS:
        return _decision("allow", f"delivery reached terminal verdict {verdict!r}")
    return _decision(
        "block", f"review-gate verdict {verdict!r} is not terminal", _GATE_VERDICT_NEXT
    )


def unreadable_state_decision() -> Decision:
    """The fail-closed decision when HEAD or the branch itself cannot be read.

    Unlike `pre_bash_response`/`pre_read_response` (fail open — a payload bug must
    not block every `Bash`/`Read` call), a turn-boundary gate that fails open
    reproduces exactly the reported failure: a silent handoff with no PR, no
    checks, no verdict. A block is recoverable by the user; a silent handoff is
    not. `MAX_CONSECUTIVE_BLOCKS` still bounds this so it cannot trap a session
    whose git state stays broken.
    """
    return _decision("block", "delivery state unreadable (git HEAD/branch)", _UNREADABLE_STATE_NEXT)


def fingerprint(
    branch: str,
    head: str,
    ci_stamp: str | None,
    gate_stamp: tuple[str, str] | None,
) -> str:
    """A stable key for "the same delivery state as last time" (budget tracking)."""
    raw = f"{branch}␟{head}␟{ci_stamp}␟{gate_stamp}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def apply_budget(
    decision: Decision,
    current_fingerprint: str,
    previous: BudgetRecord | None,
    max_blocks: int = MAX_CONSECUTIVE_BLOCKS,
) -> tuple[Decision, BudgetRecord | None]:
    """Bound a `"block"` decision by consecutive turn-ends on an unchanged fingerprint.

    An `"allow"` decision is returned unchanged and clears tracking (`None`): a
    terminal or non-delivery state has nothing left to bound. A changed
    fingerprint resets the count to 1 — the delivery advanced, so the escalation
    clock restarts rather than carrying stale blocks from a prior step forward.
    """
    if decision.action != "block":
        return decision, None
    count = 1
    if previous is not None and previous.fingerprint == current_fingerprint:
        count = previous.consecutive_blocks + 1
    record = BudgetRecord(current_fingerprint, count)
    if count > max_blocks:
        return _decision("escalate", decision.reason, decision.next_action), record
    return decision, record
