## Why

Issue 99 judges one task by six readings: cost, hours to merge beside the change size
(`lines`), plan and code review rounds, failed and denied tool calls, and compactions. The
owner reads them on dashboard `aqxk4q`, per task and as a trend across tasks. For a new task
the dashboard does not show them.

Observed on 2026-10-11 for issue-396 (PR 401), over the last 14 days:

- The live Loki and Prometheus panels group by `task_id` and `attempt_id`
  (`get_dashboard_panel_queries aqxk4q`). The *Per-task telemetry* cost query returns
  `issue-101` ($1.20) and an unlabelled bucket of $58.93, and issue-396's session
  `0d943164-…` is in the bucket. *Rule 1* counts that bucket as a rejection. `$task` lists
  `task_id` values only, so *Rule 2* cannot select issue-396.
- *Recorded readings* is correct. The CSV row of PR 401 holds all six readings with an empty
  `gap`, and its `task-readings` run succeeded. But only cost, hours, plan rounds and code
  rounds have a trend panel.

## What Changes

- The *Recorded readings* row becomes the dashboard's only per-task view, with a trend for
  every reading (design D1).
- The live rows and their variables are removed (design D2).
- The text panel, the dashboard description and
  `.agent-process/docs/telemetry-measurement-setup.md` point at the row (design D3).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The dashboard is host state, and the CSV and its workflow are unchanged
(`skip_specs`).

## Impact

- Edited: `.agent-process/docs/telemetry-measurement-setup.md`.
- Host state: dashboard `aqxk4q` (panels, variables, description).
- No ADR: the removal follows ADR 0038 and ADR 0039.
