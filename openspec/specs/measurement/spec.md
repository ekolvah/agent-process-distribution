# measurement Specification

## Purpose
How this repository records the readings of its own delivered tasks, so that the readings outlive
the raw telemetry and can be read on one dashboard.

## Requirements

### Requirement: Merged task records its readings
When a PR is merged into `main` and its head branch names a change archived on `main`, a
workflow of this repository SHALL write one row for that PR to `task-readings.csv` on the
branch `task-readings`. The row SHALL carry `pr`, `change`, `task_id`, `start`, `merged_at`,
`hours`, `lines`, `plan_rounds`, `code_rounds`, `cost_usd`, `api_requests`, `failed`,
`denied`, `compactions` and `gap`. `task_id` SHALL be `issue-<N>`, where `<N>`
comes from the change's `tracking issue <N>` token. A second run for the same PR SHALL
replace that PR's row. A file whose header names other columns SHALL be rewritten with this
header; a column the two headers share SHALL keep its values.

#### Scenario: Task PR merged
- **WHEN** a PR whose head branch is an archived change is merged
- **THEN** `task-readings.csv` on `task-readings` holds exactly one row with that PR number,
  and its `task_id` is `issue-<N>` of the change's tracking issue

#### Scenario: Re-run for a recorded PR
- **WHEN** the workflow is dispatched for a PR that already has a row
- **THEN** the file still holds exactly one row for that PR, with the new readings

#### Scenario: File with an earlier header
- **WHEN** a task PR is recorded into a file whose header has `attempt_id` and
  `unlaunched_events`
- **THEN** the file's header is the current column list, and each earlier row keeps its
  `pr`, `task_id` and `cost_usd`

### Requirement: Non-task PR records nothing
A merged PR whose head branch names no change archived on `main` SHALL leave
`task-readings.csv` unchanged, and the run SHALL succeed.

#### Scenario: Release PR merged
- **WHEN** a release PR from `release-please--branches--main` is merged
- **THEN** the run succeeds and `task-readings.csv` is unchanged

### Requirement: Unreadable reading is a gap
A reading that cannot be taken SHALL leave its cell empty, and the row's `gap` SHALL name the
cause of that empty cell. An empty cell SHALL NOT be written as `0`. A run that cannot write the
row SHALL fail.

#### Scenario: Task without telemetry
- **WHEN** a task PR is merged and its archived change records no session
- **THEN** its row has empty `start`, `hours` and telemetry cells, and `gap`
  names no bound session as their cause

#### Scenario: Bound session without telemetry
- **WHEN** one of the change's two bound sessions has a token sample and the other has none
- **THEN** the row's telemetry cells count the first session, and `gap` names the second

#### Scenario: Grafana unreachable
- **WHEN** the Grafana query fails
- **THEN** the run writes the row with empty telemetry cells and a `gap` that names the
  failure, and the run fails

### Requirement: Telemetry follows the bound sessions
The telemetry readings of a task SHALL count only the events whose `session_id` is one of
the sessions its archived change records. They SHALL cover the time from the first token sample of
those sessions to `merged_at`.

#### Scenario: Parallel session of another task
- **WHEN** a session not recorded by the change sends `api_request` events inside the
  task's window
- **THEN** those events add nothing to the row's `cost_usd` or `api_requests`

### Requirement: A session leads one task
A session already bound to another issue SHALL make `create_tracking_issue`, `start_change`
and `archive_change` exit 2 before any issue, branch, status or archive change. The message
SHALL name both issues and ask for a new session. Otherwise each script SHALL bind the session
named by `CLAUDE_CODE_SESSION_ID` to the change's tracking issue; `create_tracking_issue`
binds a newly created issue once its number is in `tasks.md`. When
`CLAUDE_CODE_SESSION_ID` is unset, the script SHALL print that the session is not bound and
SHALL continue.

#### Scenario: Second task in one session
- **WHEN** a session bound to one issue runs `start_change` for a change of another issue
- **THEN** the script exits 2, names both issues, and creates no branch

#### Scenario: Plan creates the issue
- **WHEN** an unbound session runs `create_tracking_issue` for a change without an issue
- **THEN** the session is bound to the issue the script created

#### Scenario: No session variable
- **WHEN** `start_change` runs without `CLAUDE_CODE_SESSION_ID`
- **THEN** it prints that the session is not bound and starts the change

### Requirement: The archive records the task's sessions
Before the change is archived, `archive_change` SHALL write every session bound to the
change's tracking issue into the change's `sessions` file, one id per line.

#### Scenario: Plan and implementation in two sessions
- **WHEN** one session ran `create_tracking_issue` and another ran `start_change` and
  `archive_change` for the same change
- **THEN** the archived change's `sessions` lists both session ids
