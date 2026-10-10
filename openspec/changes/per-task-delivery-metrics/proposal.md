## Why

Issue 99 judges one task by two metrics: how long it took from start to merge for its size,
and how many review rounds its plan and code took. The task identity exists since ADR 0037,
but nothing reads either metric, and one input is not recorded anywhere. The reviewer
overwrites `architect-review.json` on every round, so the archived plan keeps only the last
verdict and the plan's rework cannot be counted.

Observed on 2026-10-10 (design.md records the exact readings):

- Grafana answers `min(min_over_time(timestamp(claude_code_token_usage_tokens_total{task_id="issue-101",attempt_id="1"})[30d:1m]))`
  through the datasource proxy with `GRAFANA_URL` and `GRAFANA_SERVICE_ACCOUNT_TOKEN`, giving
  `2026-10-10T15:02:36Z`. An unknown task gives an empty result. The oldest retained sample is
  from 2026-09-26, so retention is about 14 days.
- Issue 101's timeline has one `ConnectedEvent` to PR 382: the linked branch that
  `start_change` creates with `gh issue develop`.
- PR 382 has three `github-actions` comments `Reviewed head SHA: <sha>` with distinct SHAs:
  three reviewed heads.

## What Changes

- `architect-review.json` gets a required `round` (integer ≥ 1). The schema's description
  states the rule: 1 on the first review of a change, one more than the file it replaces on
  every later review.
- New owner script `.agent-process/scripts/task_metrics.py --issue N [--attempt K]`. It prints
  one JSON reading of the task:
  - its PR, start, merge time, hours to merge and lines changed (additions + deletions);
  - plan rounds (the archived review's `round`) and code rounds (distinct reviewed heads);
  - a `gaps` list naming every value it could not read.
  It exits 1 when there is a gap and 2 on bad arguments, a missing credential, an ambiguous PR
  or a failed read.
- The start is the task's first token sample in Grafana, matched on the exact `task_id` and
  `attempt_id`. A session started without the launcher has no such series, so it never
  counts toward the task.
- `.agent-process/docs/telemetry-measurement-setup.md` gets a "Per-task readings" section: the
  command, the sources, the retention limit, and the baseline reading beside the current value.

## Capabilities

### New Capabilities

None. The readings are owner-side measurement tooling, like the ADR 0037 launcher, and not
part of the distributed process.

### Modified Capabilities

- `planning`: the architect review records its round.

## Impact

- Edited: `skills/agent-process/architect-review.schema.json`,
  `openspec/specs/planning/spec.md` (through the delta),
  `.agent-process/docs/telemetry-measurement-setup.md`,
  `tests/publisher/test_planning_workflow.py`, `tests/publisher/test_start_change.py` (the
  valid-review fixtures gain `round`).
- Added: `.agent-process/scripts/task_metrics.py`, `tests/agent_process/test_task_metrics.py`.
- Consumers: a change in flight whose review has no `round` fails `start_change` validation,
  which names `round`. A new review run fixes it. Archived reviews are not validated again.
- No ADR. The source decisions only matter to this script and are recorded in design.md. The
  doc names the sources for the reader. Telemetry metrics (cost, failed/denied calls,
  compactions) and their window-rejection rules stay with the sibling issue.
