## MODIFIED Requirements

### Requirement: Merged task records its readings
When a PR is merged into the default branch of a repository that carries the `task-readings`
workflow, and its head branch names a change archived on that branch, the workflow SHALL write
one row for that PR to `task-readings.csv` on the branch `task-readings` of that repository. A
repository without that branch SHALL get it, holding only that file, from the first run that
records a row. The row SHALL carry `pr`, `change`, `task_id`, `start`, `merged_at`,
`hours`, `lines`, `plan_rounds`, `code_rounds`, `cost_usd`, `api_requests`, `failed`,
`denied`, `compactions` and `gap`. `task_id` SHALL be `issue-<N>`, where `<N>`
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

### Requirement: Non-task PR records nothing
A merged PR whose head branch names no change archived on the default branch SHALL leave
`task-readings.csv` unchanged, and the run SHALL succeed.

#### Scenario: Release PR merged
- **WHEN** a release PR from `release-please--branches--main` is merged
- **THEN** the run succeeds and `task-readings.csv` is unchanged

## ADDED Requirements

### Requirement: Readings come from the repository's own stack
The telemetry readings of a repository's row SHALL be queried from the Grafana at that
repository's `GRAFANA_URL` variable with its `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret, and SHALL
count only events whose `vcs_repository_name` is that repository's `<owner>/<name>`.

#### Scenario: Adopter without its stack credentials
- **WHEN** a task PR is merged in a repository whose `GRAFANA_URL` variable is unset
- **THEN** that repository's row has empty telemetry cells, its `gap` names the unset
  `GRAFANA_URL`, and the run fails
