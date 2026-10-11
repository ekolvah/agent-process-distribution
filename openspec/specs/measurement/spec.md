# measurement Specification

## Purpose
How this repository records the readings of its own delivered tasks, so that the readings outlive
the raw telemetry and can be read on one dashboard.

## Requirements

### Requirement: Merged task records its readings
When a PR is merged into `main` and its head branch names a change archived on `main`, a
workflow of this repository SHALL write one row for that PR to `task-readings.csv` on the
branch `task-readings`. The row SHALL carry `pr`, `change`, `task_id`, `attempt_id`, `start`,
`merged_at`, `hours`, `lines`, `plan_rounds`, `code_rounds`, `cost_usd`, `api_requests`,
`failed`, `denied`, `compactions`, `unlaunched_events` and `gap`. `task_id` SHALL be
`issue-<N>`, where `<N>` comes from the change's `tracking issue <N>` token. A second run for
the same PR SHALL replace that PR's row.

#### Scenario: Task PR merged
- **WHEN** a PR whose head branch is an archived change is merged
- **THEN** `task-readings.csv` on `task-readings` holds exactly one row with that PR number,
  and its `task_id` is `issue-<N>` of the change's tracking issue

#### Scenario: Re-run for a recorded PR
- **WHEN** the workflow is dispatched for a PR that already has a row
- **THEN** the file still holds exactly one row for that PR, with the new readings

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
- **WHEN** a task PR is merged and no token sample of its `task_id` exists
- **THEN** its row has empty `start`, `hours` and telemetry cells, and `gap` names no
  telemetry for that `task_id` as their cause

#### Scenario: Grafana unreachable
- **WHEN** the Grafana query fails
- **THEN** the run writes the row with empty telemetry cells and a `gap` that names the
  failure, and the run fails
