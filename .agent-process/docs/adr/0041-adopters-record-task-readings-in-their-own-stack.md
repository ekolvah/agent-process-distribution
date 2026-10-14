---
status: "accepted"
date: 2026-10-13
decision-makers: ekolvah
---

# Adopters record task readings in their own stack

## Context and Problem Statement

Only this repository recorded per-task readings: the workflow was not installed in adopters,
and they held no Grafana credentials. Their sessions already export under
`vcs_repository_name="<owner>/<repo>"`
([ADR 0026](0026-project-attribution-rides-the-telemetry-resource-attributes.md)), so only the
recording was missing. [ADR 0029](0029-telemetry-leaves-the-v2-migration.md) left open whose
backend an adopter's telemetry belongs to.

## Considered Options

* Each adopter records into its own repository from its own Grafana stack
* Adopters' rows are routed to this repository and its dashboard `aqxk4q`

## Decision Outcome

Chosen: **each adopter records into its own repository from its own stack**. The plugin ships
the recording, not data routing, and `aqxk4q` keeps reading only this repository's rows.

* **D1 — the callee.** `reusable-task-readings.yml` checks out the caller's default branch and
  this repository at `job.workflow_sha` into `trusted/`, and runs
  `trusted/.agent-process/scripts/task_readings.py`, as `reusable-agent-review.yml` runs
  `head_review.py` ([ADR 0012](0012-ci-logic-is-referenced-not-copied.md)).
* **D2 — the caller.** `init` renders the managed `.github/workflows/task-readings.yml`, pinned
  to `@v<version>`; it passes the repository's `GRAFANA_URL` variable as an input and its
  `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret, neither required, so an unset one writes a gap row
  instead of the platform refusing the call. This repository's caller is the same at `@main`.
* **D3 — the branch.** The first run of a repository without `task-readings` creates it as an
  orphan holding only `task-readings.csv`, header first.
* **D4 — the manual row.** `init` prints `manual task-readings` while either credential is
  absent, from the one secret-names read it shares with `review-secret`.

### Consequences

* Good, because an adopter's readings and dashboard stay in its own account, with no shared
  credential.
* Bad, because every adopter's merged task PR runs red with a gap row until the person does the
  `manual task-readings` row.
* Bad, because the script queries Grafana Cloud's datasource UIDs `grafanacloud-prom` and
  `grafanacloud-logs`; another stack gets a `telemetry: Grafana query failed: …` gap.

### Confirmation

`tests/publisher/test_reusable_workflows.py::test_callee_reads_the_callers_stack` holds D1 and
D2, `tests/publisher/test_reusable_workflows.py::test_first_record_creates_the_branch` and
`tests/agent_process/test_task_readings.py::test_first_task_of_a_repository` D3,
`tests/publisher/test_init.py::test_task_readings_caller_render` the rendered caller, and
`tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` D4. Live: the
first merged task PR of an adopter after the release writes its row on a new `task-readings`
branch.
