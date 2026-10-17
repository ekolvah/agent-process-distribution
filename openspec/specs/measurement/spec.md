# measurement Specification

## Purpose
How a repository with the process installed records the readings of its own delivered tasks,
so that the readings outlive the raw telemetry and can be read on one dashboard.

## Requirements

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

### Requirement: Non-task PR records nothing
A merged PR whose head branch names no change archived on the default branch SHALL leave
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

### Requirement: Readings come from the repository's own stack
The telemetry readings of a repository's row SHALL be queried from the Grafana at that
repository's `GRAFANA_URL` variable with its `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret, and SHALL
count only events whose `vcs_repository_name` is that repository's `<owner>/<name>`.

#### Scenario: Adopter without its stack credentials
- **WHEN** a task PR is merged in a repository whose `GRAFANA_URL` variable is unset
- **THEN** that repository's row has empty telemetry cells, its `gap` names the unset
  `GRAFANA_URL`, and the run fails

### Requirement: The dashboard renders for a list of repositories
`agent-process dashboard <owner/name>...` SHALL print a Grafana dashboard JSON whose Infinity
datasource is the import input `DS_INFINITY`. Each data panel SHALL hold one query per listed
repository, which reads
`https://raw.githubusercontent.com/<owner/name>/task-readings/task-readings.csv` and gives
every row a `repository` column holding `<owner/name>`, and SHALL merge its queries.
In the table, `task_id` SHALL link to `https://github.com/<repository>/issues/<N>` for the
`<N>` of its `issue-<N>`. An argument that is not `<owner>/<name>` (a name of `.` or `..`
included), or no argument, SHALL exit 2 and print nothing on stdout. A repository listed twice,
in any letter case, SHALL render once, as first spelled.

#### Scenario: One repository
- **WHEN** the dashboard is rendered for `ekolvah/kinozal_scraper`
- **THEN** every data panel has exactly one query, which reads that repository's CSV through
  `${DS_INFINITY}`, and the table's `task_id` link resolves to that repository's issue

#### Scenario: Several repositories
- **WHEN** the dashboard is rendered for two repositories
- **THEN** every data panel has two queries, one per repository, each with its own
  `repository` value, and merges them into one result

#### Scenario: Repeated repository
- **WHEN** the dashboard is rendered for a repository, another, and the first again in upper case
- **THEN** every data panel has two queries, in first-listed order

#### Scenario: Malformed repository
- **WHEN** the dashboard is rendered for `kinozal_scraper`
- **THEN** the command exits 2, names the argument, and prints nothing on stdout

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

### Requirement: The dashboard draws step events per 100 requests next to the count
The rendered dashboard's `compactions` panel SHALL draw, besides the per-task count and its
trend, `compactions` per 100 `api_requests` per task on a right axis. The `failed + denied
calls` panel SHALL do the same for `failed + denied`.

#### Scenario: Rate panels
- **WHEN** the dashboard is rendered for one repository
- **THEN** each of the two panels reads `api_requests` and draws the count, its trend, and
  `per 100 requests` on the right axis, but not `api_requests`
