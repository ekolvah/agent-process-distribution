## Why

The second PR of `v2-2b-review-by-apps` (branch `issue-130-review-events`) rests on design
D6 of the archived change: a review submitted on the PR re-runs the required check on the
unchanged head, so a resolve needs no `gh run rerun` by hand and the fixer's reply after
the resolve is what re-runs the check. Observed on the PR, head `a1d0bad`: the
`pull_request` run (`35262221116`) concluded red at 19:04Z with a `P1` thread open; the
resolve and three replies started three `pull_request_review` runs that concluded green at
19:06Z; the PR stayed `mergeStateStatus: BLOCKED`. The branch protection's
`statusCheckRollup` lists every event's run as a required context of its own — the UI
shows `(pull_request)` and `(pull_request_review)` as two "Required" lines under
`agent-review` — and a review-event run leaves the `pull_request` context as it was.
`gh run rerun 35262221116` re-executed that run on the same payload, its enforcement read
the resolve, and the PR went `CLEAN`. Root cause: D6 inferred "the required context
follows the later run" from a checks listing instead of verifying the merge state on the
platform. The trigger therefore adds a second required line, a run per reply — a wait and,
on a head Codex left silent, a Claude review — and the fork and `last: 30` questions of the
fourth and fifth Codex reviews, and removes nothing. Owner's decision (2026-09-17): the
caller runs on `pull_request` alone again, and the rerun by hand returns as the step a
resolve needs.

## What Changes

- `agent-review.yml` `on`: `pull_request: [opened, synchronize]` alone; the
  `pull_request_review` trigger goes.
- `openspec/config.yaml`, Deliver group, and `agent-process.md` step 4: resolve once the
  Codex review of the new head is in → `gh run rerun <run-id>` of the head's completed
  `agent-review` run (the id from `gh pr checks <PR>`) → reply on the thread. The
  "re-runs on every later review event" and "the reply re-runs the check" clauses go.
- `review-and-merge`, "Unresolved P0/P1 threads fail the review check": the scenario
  *Review event re-runs the check* now states how the check is re-run after a resolve —
  by the fixer's rerun of the `pull_request` run, not by an event. The heading stays:
  OpenSpec 1.13.0 lets no MODIFIED delta drop a scenario.
- `implementation`, "Delivery steps are tasks of every change": the loop sentence — the
  check runs on pushes alone, the required context is the head's `pull_request` run,
  resolve → rerun → reply.
- ADR 0027: the observation with its run ids, the withdrawn design, what the PR keeps (#137).
- `reusable-agent-review.yml` is untouched: the callee runs the same path for any event a
  caller may send (scenario *Event other than a push*), which is what closes the
  enforcement-only hole whatever the trigger set.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `review-and-merge`: "Unresolved P0/P1 threads fail the review check".
- `implementation`: "Delivery steps are tasks of every change".

## Impact

- Edited: `.github/workflows/agent-review.yml`, `openspec/config.yaml` (one entry of
  `rules.tasks`), `.agent-process/docs/architecture/agent-process.md` (step 4),
  `tests/publisher/test_reusable_workflows.py` (the caller test),
  `tests/publisher/test_planning_workflow.py` (the ordering assertions), ADR 0027,
  `openspec/specs/` (by the archive alone).
- Delivered on the open PR of the tracking issue (the second PR of issue 130): no new
  issue, no new branch — the change is the delta of that PR's review fix, as the Deliver
  rule orders for a review fix that changes a spec.
