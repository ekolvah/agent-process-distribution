## Context

Panels 22 (`failed + denied calls`) and 23 (`compactions`) of
`skills/agent-process/templates/per-task-dashboard.json` read the CSV through Infinity, drop
rows with an empty reading (`filterByValue`), and draw the count with a trailing mean of 3
(`calculateField`, window). Panel 22 adds `failed` and `denied` with a binary
`calculateField`. Every target already carries an Infinity `computed_columns` entry, and
`dashboard.py` copies the whole target per repository.

## Decisions

### D1. The rate is an Infinity computed column on a right axis

Each panel's target gains the `api_requests` column and one computed column:
`compactions_per_100_requests = compactions * 100 / api_requests` and
`failed_denied_per_100_requests = (failed + denied) * 100 / api_requests`. The count line,
its `per task` override, the `filterByValue`, the window trend over the count, panel 22's
binary `calculateField` and the titles stay. `organize` hides `api_requests` (panel 22
adds it to its step; panel 23 gains the step). An override on the rate field sets display
name `per 100 requests`, unit `suffix:/100 req`, `custom.axisPlacement` `right` and a fixed
colour. The rate needs its own axis because its scale is not the count's (PR 405: 5
compactions, 1.14 per 100); the unit separates the axes, and task 4.3 renders panel 23 to
confirm it.

Observation (Grafana `/api/ds/query` on `grafanacloud-infinity`, 2026-10-17, this
repository's CSV, both expressions as computed columns): PR 401 gives `1.4598…` and
`6.5693…`, PR 433 (0 compactions, 83 requests) gives `0`, and PRs 385–397 (empty readings)
give `null`, not 0. So an empty reading stays a gap.

Alternative: a rate column written by `task_readings.py`. Rejected: a derived value in the
record and a header change for every adopter, for what render time computes.
Alternative: Grafana `calculateField` binary steps (×100, ÷`api_requests`). Rejected: two
transformations per panel where one expression does it.
Alternative: the rate replaces the count. Rejected: the reader compares both on one graph.
Deferred: a trend over the rate, a fourth line per panel; add it if the rate points prove
too noisy to read.

### D2. Only step-driven events are normalised

`api_requests` measures the agent's effort, which goal 2 minimises, not the task's size.
Compactions and failed or denied calls occur per request; cost, hours and review rounds do
not scale with requests, and cost per request would hide a task that wasted requests, so they
stay absolute. The table keeps every raw count: it is the record of the readings.

## Risks / Trade-offs

- A task with `api_requests` of 0 and a non-empty compactions reading would divide by zero.
  No such row exists: a task with telemetry has requests, and one without has empty cells.
- Rollback: re-import the previous template revision over `aqxk4q`.
