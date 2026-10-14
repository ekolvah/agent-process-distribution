## Why

Dashboard `aqxk4q` (*Per-task delivery*) exists only in the owner's Grafana. Its 7 panel
targets read `https://raw.githubusercontent.com/ekolvah/agent-process-distribution/task-readings/task-readings.csv`
through the datasource `grafanacloud-infinity` (`get_dashboard_by_uid aqxk4q`, 2026-10-14).
An adopter that records its own readings (ADR 0041) has no dashboard for them, and a person
with several repositories cannot see all their tasks in one table. `task_id` is `issue-<N>`
with no link to the issue. ekolvah/kinozal_scraper#642 records this gap.

Observed on the owner's stack on 2026-10-14 (`POST /api/ds/query`, Infinity backend parser):

- A computed column whose selector is a string literal adds that string to every row:
  `'ekolvah/agent-process-distribution'` as `repository` returned it beside `pr` 382.
- `replace(task_id, 'issue-', '')` as a computed column returned `101` for `issue-101`;
  `trimPrefix` is `Undefined function`.
- A CSV URL that answers 404 (`ekolvah/kinozal_scraper`, which has no `task-readings` branch
  yet) fails only its own query, with `unsuccessful HTTP response code … 404 Not Found`.

## What Changes

- The plugin ships the dashboard as a template, `templates/per-task-dashboard.json`. It is
  `aqxk4q` with the Infinity datasource as an import input `DS_INFINITY`, and one prototype
  query per panel.
- A new `agent-process dashboard <owner/name>...` prints the dashboard for the listed
  repositories. Every data panel gets one query per repository, which reads that
  repository's CSV and adds a `repository` column, and merges them. One repository gives a
  per-project dashboard; several give one dashboard that holds all their tasks.
- In the table, `task_id` links to `https://github.com/<repository>/issues/<N>`.
- The `manual task-readings` row of `init` also names the render command and Grafana's Import.
- `aqxk4q` is re-imported from the render for this repository, keeping its UID.
- ADR 0042 records the decision. `telemetry-measurement-setup.md` documents rendering and
  importing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `measurement`: a new requirement covers the dashboard render for a list of repositories.
- `distribution`: the `manual task-readings` row of *Actions credentials are printed, not
  set* also names the dashboard render and its import.

## Impact

- Added: `skills/agent-process/scripts/dashboard.py`,
  `skills/agent-process/templates/per-task-dashboard.json`, `tests/publisher/test_dashboard.py`,
  `.agent-process/docs/adr/0042-the-per-task-dashboard-renders-for-a-list-of-repositories.md`.
- Edited: `skills/agent-process/scripts/manual.py` (the row text),
  `.agent-process/docs/telemetry-measurement-setup.md`, `tests/publisher/test_plugin.py`
  (`MOVED_SCRIPTS`, `TEMPLATES`), `tests/publisher/test_init_remote.py` (the readings row).
- Removed: none.
- Host state: dashboard `aqxk4q` in the owner's Grafana.
