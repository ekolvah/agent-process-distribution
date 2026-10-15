## Why

`hours` (first token sample to merge) mixes the agent's work with the wait for the person. In
`task-readings.csv` on 2026-10-15, PR 417 and PR 422 read 22.88 and 21.89 hours, and their last
commits were 21 hours before the merge (`gh pr view <N> --json createdAt,mergedAt,commits`).
The dashboard cannot tell agent time from waiting time, so it cannot show which one to shorten.
`hours` stays as the full picture.

Platform facts:

- Claude Code documents `claude_code.active_time.total` (unit `s`) as "Total active time" with
  "`type`: `"user"` for keyboard interactions, `"cli"` for tool execution and AI responses"
  ([monitoring reference](https://code.claude.com/docs/en/monitoring-usage)).
- Observed in `grafanacloud-prom` on 2026-10-15: `claude_code_active_time_seconds_total`
  carries `session_id`, `type` and `vcs_repository_name`. Over 14 days it has series with both
  `type="cli"` and `type="user"`. `sum by (session_id) (max_over_time(…{type="cli"}[5d]))`
  gives 2333 s for PR 422's session, 2770 s for PR 419's and 5458 s for PR 417's. PR 422's
  session has two series, which differ only in account labels (`organization_id`,
  `user_email`), 2259 s and 74 s.
- Observed: the counter resets, rarely. Over `[14d]` with
  `vcs_repository_name="ekolvah/agent-process-distribution",type="cli"`,
  `count(count by (session_id) (…))` gives 99 sessions, and `resets(…) > 0` holds for 2 of them
  (`43b7bee7-…`, `9d152acd-…`). Each series' `increase()` came 5–12% under its `max_over_time` on the sessions
  above, because the first sample is not counted.

## What Changes

- `task-readings.csv` gains `agent_hours`: the `type="cli"` active time of the task's bound
  sessions, in hours. `hours` is unchanged.
- The dashboard's hours panel draws `agent_hours` beside `hours` on the same axis. The table
  gets the column next to `hours`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `measurement`: the readings row carries `agent_hours`, and the dashboard shows it with
  `hours`.

## Impact

- Edited: `.agent-process/scripts/task_readings.py`,
  `tests/agent_process/test_task_readings.py`,
  `skills/agent-process/templates/per-task-dashboard.json`,
  `tests/publisher/test_dashboard.py`, `.agent-process/docs/telemetry-measurement-setup.md`.
- Added: none. Removed: none.
- Host state: dashboard `aqxk4q` is re-imported from the template. Adopters re-render their
  dashboard to get the series. Their rows get the column from the release their workflow pins.
