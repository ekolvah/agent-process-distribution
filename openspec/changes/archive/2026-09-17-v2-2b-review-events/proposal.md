## Why

Review fixes of PR #137 (the second PR of `v2-2b-review-by-apps`, branch
`issue-130-review-events`) changed what two specs require, and rounds 3 and 4 (`b6858f8`,
`26bc2da`) wrote those changes into `openspec/specs/` directly: the change of the PR was
archived before the PR opened, as the process orders, and no delta described the new
behaviour. Codex's review of `26bc2da` named it (P1, "Add a delta before changing the target
spec"), and the owner decided: a review fix that changes a spec goes through a change of its
own. This change is that delta — for the behaviour the fixes introduced and for the rule
that requires the delta from now on. Reproduction of the gap: `git diff main..26bc2da --
openspec/specs` is non-empty while `openspec/changes/` holds no change of this branch.

## What Changes

- `review-and-merge`: the Claude fallback runs only for a head in the repository itself
  (scenario *Head from a fork*); every event runs the same path — wait, fallback on absence,
  verification, enforcement (scenario *Event other than a push*); a submitted review, a
  reply on a thread included, re-runs the check on the unchanged head (scenario *Review
  event re-runs the check*). The workflow, the caller and their tests are already on the
  branch (`b6858f8`, `26bc2da`); this delta is their spec.
- `implementation`, "Delivery steps are tasks of every change": the loop resolves an
  addressed thread once the Codex review of the new head is in and replies after the
  resolve; and a review fix that changes a spec goes through a change of its own on the PR
  branch — delta, `validate --strict`, `archive_change` — never a direct edit of
  `openspec/specs/` (scenario *Review fix changes a spec*).
- `openspec/config.yaml`, Deliver group, and `agent-process.md` step 4 name the spec-fix
  rule; `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` asserts it.
- `openspec/specs/` on the branch is reverted to `main`; the archive of this change applies
  the delta — the same text, carried the way the process carries a spec.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `review-and-merge`: "Codex reviews on the author's request, Claude is the fallback" and
  "Unresolved P0/P1 threads fail the review check".
- `implementation`: "Delivery steps are tasks of every change".

## Impact

- Edited: `openspec/config.yaml` (one entry of `rules.tasks`), `agent-process.md` (step 4),
  `tests/publisher/test_planning_workflow.py` (one assertion), `openspec/specs/` (by the
  archive alone), ADR 0027 (the observation of the reply-driven re-run and this decision).
- No new script. Delivered on the open PR #137 of tracking issue #130: no new issue, no
  new branch — the change is the delta of that PR's review fixes, not a unit of its own.
