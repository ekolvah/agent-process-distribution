## Why

Issue 99 judges a delivered task by five metrics, but they are split today. Dashboard `aqxk4q`
reads the telemetry metrics live from Loki and Prometheus. The GitHub metrics are read by
hand ([setup doc](../../../../.agent-process/docs/telemetry-measurement-setup.md#per-task-readings)) and are on no
dashboard. Once the raw telemetry expires, a task's telemetry readings are gone. Tracking
issue 389.

Observed on 2026-10-11:

- **The stack is on the free plan.** `grafanacloud_instance_info` and
  `grafanacloud_logs_instance_info` (datasource `grafanacloud-usage`) carry
  `org_grafana_cloud="free"`. `grafanacloud_logs_instance_limits{limit_name="retention_period"}`
  is `2678400000000000` ns, which is 31 days. The oldest `claude_code_token_usage_tokens_total`
  sample is 2026-09-25T04:19:55Z. A Prometheus query longer than 768 h fails with
  `err-mimir-max-query-length`. A reading pushed into Prometheus or Loki expires like the
  raw telemetry.
- **The dashboard can read this repository.** The repository is public. Datasource
  `grafanacloud-infinity` has empty `jsonData`, so it has no allowed-hosts list. A `/api/ds/query`
  call fetched
  `https://raw.githubusercontent.com/ekolvah/agent-process-distribution/main/openspec/changes/archive/2026-10-10-per-task-delivery-metrics/architect-review.json`
  with status 200 and returned its five top-level fields as a table.
- **The readings exist only after the merge.** `archive_change` runs before `gh pr create`
  (SKILL.md, Delivery). The merge time, the code review rounds, and the telemetry of those
  rounds are not available at archive. The person chose to record the readings with a
  workflow after the merge.
- **Only `main` and `stable` are protected.** Rulesets `agent-process default branch` and
  `pr-title` target `refs/heads/main` / `~DEFAULT_BRANCH`. `stable channel` targets
  `refs/heads/stable`. A data branch can take a workflow push.
- **The Loki proxy takes GET only.** A POST to `/api/datasources/proxy/uid/grafanacloud-logs/loki/api/v1/query`
  returned 403 `non allow-listed POSTs not allowed on proxied loki datasource`. The same query
  as a GET returned 200.

## What Changes

- A new owner-side workflow `.github/workflows/task-readings.yml` runs when a PR is merged
  into `main`, and on `workflow_dispatch` with a PR number. It runs
  `.agent-process/scripts/task_readings.py`.
- The script handles one merged PR. A PR whose head branch has no archived change on `main`
  is not a task, so the script exits 0 and writes no row. For a task PR, the script reads the
  GitHub metrics and the telemetry metrics and appends one row to `task-readings.csv` on the
  unprotected branch `task-readings`. The row is keyed by `task_id` / `attempt_id`.
- A reading that cannot be taken leaves its cell empty, and the row's `gap` column names the
  reading and the cause. If the row itself cannot be written, the run fails.
- Dashboard `aqxk4q` gets a "Recorded readings" row of panels. They read the CSV through
  `grafanacloud-infinity`: a table per task, and the readings over merge time.
- The setup document's "Per-task readings" section points at the recorded file. The
  hand-read readings move into that file.

## Capabilities

### New Capabilities

- `measurement`: how this repository records the readings of its own delivered tasks. This is
  owner-side, and the installer does not distribute it.

### Modified Capabilities

None.

## Impact

- Added: `.github/workflows/task-readings.yml`, `.agent-process/scripts/task_readings.py`,
  `tests/agent_process/test_task_readings.py`,
  `openspec/specs/measurement/spec.md` (through the delta).
- Edited: `.agent-process/docs/telemetry-measurement-setup.md` ("Per-task readings").
- Host and repository state, changed once with the person's confirmation: the repository
  secret `GRAFANA_SERVICE_ACCOUNT_TOKEN` (a Viewer service account), the variable
  `GRAFANA_URL`, the branch `task-readings`, and the panels of dashboard `aqxk4q`. The
  dashboard is not kept in git.
- No new dependency. The script uses `urllib` and the existing `gh_io.run_gh`.
- No ADR. The decisions apply only to this repository's own measurement, and they are
  recorded in design.md.
