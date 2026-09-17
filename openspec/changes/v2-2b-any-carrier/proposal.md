## Why

The Deliver rule, step 4 of `agent-process.md` and the `implementation` spec (carried by
`v2-2b-push-only`) keyed the resolve of an addressed `P0`/`P1` thread to "the Codex
review of the new head is in". Codex's `P1` on head `8f272f3` of the second PR of
`v2-2b-review-by-apps` (thread `PRRT_kwDOUAa7yM6jgJkC`): on a head Codex left silent the
`agent-review` check runs the Claude fallback and the head is reviewed all the same, yet
that condition never becomes true — the addressed thread cannot be resolved by the rule's
letter and the required check stays red. Root cause: the wait was written for the path the
PR had observed (Codex reviewed every head) and not for the fallback path the spec itself
supports. `wait_for_pr.py` already returns on the concluded check whichever carrier
reviewed the head; the texts said less than the script does.

## What Changes

- `openspec/config.yaml`, Deliver group: `wait_for_pr.py <PR>` again returns on the
  concluded check of the head, whose review is Codex's or the fallback's when none came —
  then the resolve.
- `agent-process.md` step 4: "Resolve once the review of the new head is in — Codex's, or
  the fallback's the check ran when none came".
- `implementation`, "Delivery steps are tasks of every change": the loop sentence keyed to
  the review of the head by either carrier.
- ADR 0027: the observation on the review-event bullet.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `implementation`: "Delivery steps are tasks of every change".

## Impact

- Edited: `openspec/config.yaml` (one entry of `rules.tasks`),
  `.agent-process/docs/architecture/agent-process.md` (step 4),
  `tests/publisher/test_planning_workflow.py` (one assertion), ADR 0027, `openspec/specs/`
  (by the archive alone).
- Delivered on the open PR of the tracking issue (the second PR of issue 130), as the delta
  of that PR's review fix; no new issue, no new branch.
