## Why

The `compactions` and `failed + denied calls` panels of the per-task dashboard draw absolute
counts. Both events happen per agent step, so a count mixes the task's size with a process
problem, and the largest task stands out rather than the one that went wrong. Observed in
`task-readings.csv` (branch `task-readings`, 2026-10-17):

| PR | `api_requests` | `compactions` | per 100 requests |
| --- | --- | --- | --- |
| 405 agent-identity | 440 | 5 | 1.14 |
| 401 traces-from-every-session | 274 | 4 | 1.46 |
| 417 adopter-task-readings | 279 | 4 | 1.43 |

By count, 405 is the worst task; by rate, 401 and 417 grew their context fastest.

## What Changes

- Panels `compactions` and `failed + denied calls` draw their event per 100 `api_requests`
  per task, with their trend, instead of the count (design D1, D2).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `measurement`: a new requirement, *The dashboard draws step events per 100 requests*.

## Impact

- Edited: `skills/agent-process/templates/per-task-dashboard.json` (panels 22 and 23),
  `tests/publisher/test_dashboard.py` (one test added),
  `.agent-process/docs/telemetry-measurement-setup.md` (the `aqxk4q` paragraph).
- Dashboard `aqxk4q` is re-imported from the render.
