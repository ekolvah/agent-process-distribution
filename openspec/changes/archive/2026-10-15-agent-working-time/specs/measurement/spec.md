## MODIFIED Requirements

### Requirement: Merged task records its readings
When a PR is merged into the default branch of a repository that carries the `task-readings`
workflow, and its head branch names a change archived on that branch, the workflow SHALL write
one row for that PR to `task-readings.csv` on the branch `task-readings` of that repository. A
repository without that branch SHALL get it, holding only that file, from the first run that
records a row. The row SHALL carry `pr`, `change`, `task_id`, `start`, `merged_at`,
`hours`, `agent_hours`, `lines`, `plan_rounds`, `code_rounds`, `cost_usd`, `api_requests`,
`failed`, `denied`, `compactions` and `gap`. `task_id` SHALL be `issue-<N>`, where `<N>`
comes from the change's `tracking issue <N>` token. A second run for the same PR SHALL
replace that PR's row. A file whose header names other columns SHALL be rewritten with this
header; a column the two headers share SHALL keep its values.

#### Scenario: Task PR merged
- **WHEN** a PR whose head branch is an archived change is merged
- **THEN** `task-readings.csv` on `task-readings` holds exactly one row with that PR number,
  and its `task_id` is `issue-<N>` of the change's tracking issue

#### Scenario: First task of a repository
- **WHEN** a task PR is recorded in a repository that has no `task-readings` branch
- **THEN** the repository has a `task-readings` branch whose `task-readings.csv` holds the
  column header and that PR's row

#### Scenario: Re-run for a recorded PR
- **WHEN** the workflow is dispatched for a PR that already has a row
- **THEN** the file still holds exactly one row for that PR, with the new readings

#### Scenario: File with an earlier header
- **WHEN** a task PR is recorded into a file whose header has `attempt_id` and
  `unlaunched_events`
- **THEN** the file's header is the current column list, and each earlier row keeps its
  `pr`, `task_id` and `cost_usd`

## ADDED Requirements

### Requirement: Agent time is the sessions' CLI active time
`agent_hours` SHALL be the sum, over the task's bound sessions, of the Claude Code active time
with `type="cli"` over the telemetry window, in hours. A bound session with a token sample
whose active-time counter resets inside that window, or that has no active-time sample, makes
`agent_hours` a reading that cannot be taken.

#### Scenario: Agent time recorded
- **WHEN** a task's two bound sessions report 1800 and 900 seconds of `cli` active time
- **THEN** the row's `agent_hours` is `0.75` and its `hours` is unchanged

#### Scenario: Counter reset
- **WHEN** the active-time counter of one bound session resets inside the task's window
- **THEN** the row's `agent_hours` is empty, its other telemetry cells are written, and `gap`
  names that session

### Requirement: The dashboard shows agent time beside hours
The rendered dashboard's hours panel SHALL draw `hours` and `agent_hours` per task. The table
SHALL show `agent_hours` next to `hours`.

#### Scenario: Hours panel
- **WHEN** the dashboard is rendered for one repository
- **THEN** its hours panel reads both `hours` and `agent_hours` under distinct display names,
  and the table orders `agent_hours` right after `hours`
