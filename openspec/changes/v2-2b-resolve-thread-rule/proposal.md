## Why

Bug in the delivery flow, observed on PR #133 (2026-09-17): the implementer, after a context
compaction, resolved the two BLOCKING Codex threads with a raw `gh api graphql` mutation
instead of `.agent-process/scripts/resolve_review_thread.py`, and the auto-mode classifier
blocked it — the person had to ask why. Reproduction: `python -m pytest
tests/publisher/test_planning_workflow.py -q -k tasks_of_a_new_change` with the assertion
`rule.index("request_codex_review.py") < rule.index("resolve_review_thread.py")` fails on
the current `openspec/config.yaml` (no `resolve_review_thread` in the `tasks` rule at all).
Root cause: the `Deliver group` entry of the `tasks` rule — the text `/opsx:apply` puts into
every `tasks.md` — says "apply every unresolved thread, push, re-request" and never names
how an addressed BLOCKING thread is resolved; the script is named only in the v1 delivery
flow (`agent-process.md`, step 6) and ADR 0022, which the apply never loads. Whatever is not
in the `tasks` rule does not survive a compaction or a carrier switch.

## What Changes

- `openspec/config.yaml`, `rules.tasks`, Deliver group: the review loop names the resolve
  step — a BLOCKING thread the push addressed is resolved with
  `python .agent-process/scripts/resolve_review_thread.py --repo <owner/repo> --pr <PR>
  --thread <id>` (`--list` prints the open ones) before the `agent-review` run on that head
  reaches its last step; other threads (P2, nitpicks) are answered, not resolved, by the
  process.
- `openspec/specs/implementation/spec.md`: the requirement "Delivery steps are tasks of
  every change" names the resolve step, with one scenario "Blocking thread addressed".
- `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` asserts the
  order `request_codex_review.py` → `resolve_review_thread.py` in the rule.
- No new script, no duplicated prose: `agent-process.md` step 6 and ADR 0022 carry the
  rationale (the fixer resolves from the local authenticated session; CI never infers a
  thread's disposition) and stay as they are.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `implementation`: "Delivery steps are tasks of every change" — the review loop of the
  Deliver group SHALL name `resolve_review_thread.py` for the BLOCKING threads a push
  addressed.

## Impact

- Edited: `openspec/config.yaml` (one entry of `rules.tasks`),
  `openspec/specs/implementation/spec.md` (via this change's delta, applied by the
  archive), `tests/publisher/test_planning_workflow.py` (one test extended).
- Added, removed: none. No code path changes: `resolve_review_thread.py`,
  `review_gate.py` and their tests are untouched.
- Every change proposed after the archive carries the step in its `tasks.md`; changes
  proposed before it (the untracked `v2-2-delivery`) keep their old Deliver group until
  their tasks are regenerated.
