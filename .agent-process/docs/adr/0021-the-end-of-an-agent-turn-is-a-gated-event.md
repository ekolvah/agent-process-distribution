---
status: "accepted"
date: 2026-09-03
decision-makers: ekolvah
---

# The end of an agent turn is a gated event

## Context and Problem Statement

During issue #55 delivery (PR #60, implementer = Claude `/agent-process:implement`)
the agent returned a final response after starting local CI, before
`open_pr.py`, before any GitHub check, and before a `review_gate.py` verdict.
The user expected delivery to remain active until `ready-for-human`.

The "stay active until the gate ends the loop" rule existed only as prose in
the adapter files — `.agents/skills/implement-issue/SKILL.md` step 8 ("Stay
active through the review/fix loop") and `commands/implement.md` step 5.
Nothing observed the end of an agent turn. The delivery flow's one
non-deterministic event is a tool timeout on `ci_check.py`, whose full run
routinely exceeds the harness Bash timeout; with no gate on the turn
boundary, that timeout read to the agent as a terminal event and the session
handed off with no PR, no checks, and no verdict.

Every other step of the flow is already a script with an exit code
(`check_red.py`, `ci_check.py`, `open_pr.py`, `review_gate.py`). The turn
boundary was the last prose-only step — exactly the case
[principles.md §Scripts over instructions](../architecture/principles.md#scripts-over-instructions)
names: a rule phrased as "must not forget to stay active" belongs in a gate,
not in a sentence an agent skips at the end of a long pipeline. A stronger
sentence is not a fix — the sentence already existed and was already skipped.

## Considered Options

* Reword the adapter prose more forcefully ("you must not stop until...").
  Rejected: the sentence already existed and was already skipped; strength of
  wording does not change whether anything reads the turn boundary.
* Query GitHub per turn (`gh pr checks`, `review_gate.py`) directly from the
  turn-boundary hook. Rejected: firing a live network read and a full
  review-gate evaluation on every turn end of every session — including
  non-delivery sessions — is unbounded cost for a decision that a local,
  already-written stamp answers for free; it would also start a
  `review_gate.py`/`gh` process from inside the hook, reproducing the process
  sprawl `check_red.py`-style gates are meant to avoid.
* A tracked state file the agent itself updates at each step. Rejected: an
  agent-maintained file is exactly the kind of self-reported state this
  process already distrusts (the finding that started this ADR *was*
  self-reported completion); it would need its own gate to be trustworthy,
  which is circular.
* Derive delivery state from local, git-ignored stamps two existing scripts
  already write for their own purposes (`.ci_check_stamp` from `ci_check.py`),
  plus one new stamp `review_gate.py` writes for its own verdict
  (`.review_gate_stamp`), read by a pure decision table and enforced by a
  Claude `Stop` hook.

## Decision Outcome

Chosen: **derive terminal state from local stamps, enforce it on the `Stop`
event, fail closed on unreadable state, bound the block.**

1. **New gate class.** `.claude/settings.json` gains a `Stop` hook — the
   flow's first session-lifecycle hook; previously only
   `PreToolUse`/`PostToolUse` existed. It fires `hooks.py stop`, which reads
   two local git values (`git branch --show-current`, `git rev-parse HEAD`)
   and two single-writer stamp files, and launches no other process — not
   `ci_check.py`, not `gh`, not `review_gate.py`.
2. **State model.** `.agent-process/scripts/delivery_state.py` is a
   transport-neutral pure-function decision table
   (`decide(branch, head, ci_stamp, gate_stamp) -> Decision`), the shape of
   `agent_policy.py`/`navigation_policy.py`, so a future Codex adapter (issue
   #75) is a wiring change, not a redesign. `TERMINAL_VERDICTS =
   {"ready-for-human", "escalate"}`; every other verdict, and a missing or
   stale record, is progress. Off an issue branch the gate is inert.
3. **`review_gate.py` gains a local write.** It already computed the verdict
   correctly; it now records `<head> <verdict>` to `.review_gate_stamp` on
   every run (including its own capture-failure exit, stamped `gate-error`,
   itself non-terminal by construction — no special-casing needed) so the
   Stop hook can read the last verdict without a second `gh` call.
4. **Fail direction inverts this repository's established pattern.** Unlike
   `pre_bash_response`/`pre_read_response`, which fail *open* — a payload bug
   must not block every `Bash`/`Read` call — an unreadable git state at the
   turn boundary fails *closed* (`unreadable_state_decision`): the reported
   failure mode was a silent handoff with no PR, no checks, no verdict, and a
   block is recoverable by the user while a silent handoff is not.
5. **The block is bounded.** `MAX_CONSECUTIVE_BLOCKS = 5` (a code constant —
   a per-turn anti-trap budget with a single caller, not catalogue data like
   `fixer.max_runs`) caps consecutive turn-ends on an *unchanged* state
   fingerprint; past the bound the turn is allowed to end, but only with a
   visible `systemMessage` marker naming the incomplete delivery and the next
   command — never a silent allow, never an inescapable loop (§IV).

### Consequences

* Good, because a delivery can no longer hand off silently mid-flight: the
  failure mode observed in #55 (terminal response before `open_pr.py`, before
  any check, before a verdict) is now a blocked turn end, not a completed
  session.
* Good, because the decision table is transport-neutral, so issue #75's Codex
  wiring reuses it without touching the state model.
* Good, because the fail-closed inversion is scoped to exactly one hook with
  exactly one caller, rather than changing the fail-open default the other
  hooks rely on.
* Bad, because a `Stop` hook is a new surface an operator must understand:
  an agent turn that "won't end" is intentional here, not a hang — the
  `systemMessage` escalation marker after `MAX_CONSECUTIVE_BLOCKS` is the
  signal that distinguishes the two, and a reader unfamiliar with this ADR
  could mistake sustained blocking for a bug.
* Bad — residual risk, stated plainly. The gate trusts local, git-ignored
  stamp files it does not itself write; a hand-edited or stale
  `.ci_check_stamp`/`.review_gate_stamp` would misinform the decision the
  same way a hand-edited issue body already carries this process's existing
  self-reported-input trust level (ADR 0020's residual-risk precedent). This
  decision does not raise or lower that trust level, it only extends where a
  local stamp is read from.

**Assumption and rollback.** Assumes a `Stop` hook firing on every turn end,
including short informational turns, costs two `git` calls and two small file
reads — negligible relative to the harness round trip. If that assumption
proves false (measurable turn-end latency regression reported), the rollback
is to drop the `Stop` entry from `.claude/settings.json`; the decision table
and the stamps remain harmless dead weight until a future adapter reads them.

### Confirmation

`tests/publisher/test_delivery_state.py` (`TestDeliveryBlocker`,
`TestBlockBudget`) covers the decision table and the block budget;
`tests/publisher/test_hooks.py::TestStopHook` covers the adapter, including
the injected-runner assertion that no `ci_check.py`/`gh`/`review_gate.py`
process is launched; `tests/agent_process/test_delivery_gate_wiring.py` (+
`template/` twin) asserts the rendered `.claude/settings.json` actually wires
the hook — a gate nothing invokes would reproduce this issue's own root
cause; `tests/agent_process/test_review_gate.py::TestVerdictStamp` (+
`template/` twin) covers the new local write. Relates to
[ADR 0020](0020-a-tracked-deferral-downgrades-a-matching-review-finding.md)
(the closest prior precedent for stating residual trust-level risk plainly
rather than implying a gate is airtight).
