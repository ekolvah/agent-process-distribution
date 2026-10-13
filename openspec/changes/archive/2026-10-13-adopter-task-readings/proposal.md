## Why

Adopters get no per-task readings: the workflow is not installed and they have no Grafana
credentials (observed in ekolvah/kinozal_scraper, tracking issue). Their sessions already
export under `vcs_repository_name="<owner>/<repo>"` (ADR 0026), so only the recording is
missing.

Decision of the issue: telemetry backends belong to each adopter. An adopter records readings
into its own repository from its own Grafana stack; the plugin ships the recording, not data
routing, and `aqxk4q` keeps reading only this repository's rows. This settles what ADR 0029
left open.

## What Changes

- The recording job moves into a reusable workflow `reusable-task-readings.yml`. It runs
  `task_readings.py` from the process source checked out at the called commit, the way
  `reusable-agent-review.yml` runs `head_review.py`, over the caller's merged default branch.
  The script stays in `.agent-process/scripts/`.
- When the caller has no `task-readings` branch yet, the first run creates it, and the script
  writes the CSV header into an absent file.
- `init` renders a managed caller `.github/workflows/task-readings.yml`, pinned to
  `@v<version>`. This repository's `task-readings.yml` becomes the same caller at `@main`, as
  its `agent-review.yml` is.
- `init` prints a `manual task-readings` row while the repository lacks the `GRAFANA_URL`
  variable or the `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret of its own stack.
- `telemetry-measurement-setup.md` gains an adopter section; ADR 0041 records the decision.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `measurement`: a repository with the process installed records its own merged tasks, on its
  default branch, into a `task-readings` branch the first run creates, from the Grafana stack
  its own variable and secret name.
- `distribution`: the installed footprint gains the managed task-readings caller; a new
  requirement for that caller; the review-secret requirement, renamed, also covers the
  `manual task-readings` row; the observed-done state includes the two Grafana credentials.

## Impact

- Added: `.github/workflows/reusable-task-readings.yml`,
  `skills/agent-process/templates/task-readings.yml`,
  `.agent-process/docs/adr/0041-adopters-record-task-readings-in-their-own-stack.md`.
- Edited: `.github/workflows/task-readings.yml` (becomes a caller),
  `.agent-process/scripts/task_readings.py` (absent CSV), `skills/agent-process/scripts/init.py`
  (step, docstring), `skills/agent-process/scripts/manual.py` (row),
  `skills/agent-process/SKILL.md` (Install step 4 names the row),
  `.agent-process/docs/telemetry-measurement-setup.md` (adopter section, script location),
  `tests/agent_process/test_task_readings.py`, `tests/publisher/test_reusable_workflows.py`,
  `tests/publisher/test_init.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/init_harness.py`, `tests/publisher/test_plugin.py`.
- Removed: none.
- Not touched: dashboard `aqxk4q` (the adopter dashboard template is a separate issue).
