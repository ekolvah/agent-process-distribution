## Why

Observed on the three PRs of the previous step (#122, #123, #124): the Deliver group of the `tasks` rule
opens the PR first and archives the change last, so `finish_change.py` ends with a push of
the archive commit. The required `agent-review` check binds to the head SHA (v1, until
`v2-4`), so that push forces one more `request_codex_review.py --request` and one more
review round — spent on a mechanical `openspec archive -y` that changes no code (on #124
the round waited ~30 min for the workflow to start). The archive commit lands after the
last review, so the reviewer never sees the archived `tasks.md` with its Deliver ticks
(#123 thread on `finish_change` rejecting uncommitted ticks is about that gap). Root cause:
the order of the Deliver group, not the script. Tracking issue (#125), step 1b of the v2 plan (#107).

Same rule, second observation (#123 review): Group 0 creates the tracking issue and only
then asks for its priority; a person who declines leaves an issue without the mandatory
field.

## What Changes

- Deliver group order: `git status --short` empty → `archive_change.py <change>` (marks
  its own task, `openspec archive -y`, removes the lock, commits, pushes) → `gh pr create`
  → `request_codex_review.py --request` → `wait_for_pr.py` → the review loop (three rounds;
  the fourth leaves the rest to the person). The person merges. The tasks after the archive
  are ticked in `openspec/changes/archive/<date>-<change>/tasks.md`, and a re-run of the
  apply on an open PR continues from the first unchecked task there.
- `finish_change.py` becomes `archive_change.py`: no post-archive review request, no
  `wait_for_pr` inside it — those are the PR tasks that follow.
- Group 0 asks for the priority before `gh issue create`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `implementation`: the archive precedes the PR (`archive_change` replaces `finish_change`;
  the delivery tasks end with the review loop, not the archive).
- `planning`: a behaviour change archives before its PR opens, so the reviewed head is the
  archived one.

## Impact

- Renamed: `.agent-process/scripts/finish_change.py` → `archive_change.py` (shrunk).
- Edited: `openspec/config.yaml` (`tasks` rule: Group 0 order, Deliver group),
  `openspec/specs/{implementation,planning}/spec.md` (via the deltas),
  `.agent-process/docs/architecture/agent-process.md` (the one sentence naming the last
  task), ADR 0027 (observation), `tests/publisher/test_delivery_scripts.py`,
  `tests/publisher/test_planning_workflow.py`.
- Unchanged: `wait_for_pr.py`, `request_codex_review.py` (v1, until `v2-4`), the review
  budget.
