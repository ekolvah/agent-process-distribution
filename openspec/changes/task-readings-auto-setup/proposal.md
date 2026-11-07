## Why

`agent-process init` ends with a `manual task-readings` row (tracking issue 473): set the
`GRAFANA_URL` variable and the `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret, render the per-task
dashboard and import it with the Infinity datasource. Until the person notices it, every merged
task PR of the adopter runs red with a `telemetry: unset …` gap
([ADR 0041](../../../.agent-process/docs/adr/0041-adopters-record-task-readings-in-their-own-stack.md)
Consequences).

**Reproduction** (observation recorded in the issue, 2026-11-06, `ekolvah/lampa-mediacenter`
after its install PR merged): the agent finished the row alone from the machine's own state —
the URL from `~/.claude.json` → `mcpServers.grafana.env.GRAFANA_URL`; the token file that
config names (`GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE`) piped to `gh secret set` on stdin; the
Infinity datasource `grafanacloud-infinity` from `GET /api/datasources`; the rendered
dashboard with `${DS_INFINITY}` replaced, `POST /api/dashboards/db` → `200 success`. Creating a
dedicated service account answered `403 … Permissions needed: serviceaccounts:create`.

Re-observed on this machine, 2026-11-07: `mcpServers.grafana.env` holds exactly
`GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` and `GRAFANA_URL` (host `graciousdogwood2167.grafana.net`);
`GET /api/datasources` lists `{"name":"grafanacloud-infinity","type":"yesoreyeram-infinity-datasource","uid":"grafanacloud-infinity"}`
beside eleven others, so the datasource is chosen by `type`, not name. The OTLP endpoint of
`~/.claude/settings.json` has host `otlp-gateway-prod-eu-central-0.grafana.net`, which names
no stack: it is not a URL source.

**Root cause**: the requirement *Actions credentials are printed, not set* and ADR 0041 D4 make
`init` print the row unconditionally, because `init` had no source for the stack's URL and a
token. The Grafana MCP server config of the machine is that source.

## What Changes

- With the machine's Grafana MCP config, `init` sets the variable, the secret and the
  dashboard itself, as three `task-readings-*` steps.
- The `manual task-readings` row remains only for what `init` could not set up, ending with
  the reason.
- ADR 0048 records the decision and amends ADR 0041 D4; the skill's Install section and the
  measurement setup doc follow.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `distribution`: *Actions credentials are printed, not set* keeps the review secret and hands
  the task-readings row to the new requirement *Task readings are set up, or printed with the
  reason*.

## Impact

- Added: `skills/agent-process/scripts/readings_setup.py` (the `urllib` Grafana client and the
  three steps); `tests/publisher/test_init_readings.py`;
  `.agent-process/docs/adr/0048-init-sets-up-task-readings-from-the-grafana-mcp-config.md`.
- Edited: `skills/agent-process/scripts/init.py` (the steps in the run, the Grafana factory,
  `input` on `Context.call`); `skills/agent-process/scripts/steps.py` (`run` moved here with
  an `input` argument, keeping `init.py` within `max-module-lines = 1000`);
  `skills/agent-process/scripts/manual.py` (the `Grafana` Protocol, the reader, the row from
  it, the factory on `Target`, variable values in the variable read);
  `tests/publisher/init_harness.py` (`gh variable set`, `gh secret set` and
  `variable list --json name,value` in `FakeGitHub`, an in-memory Grafana); `tests/publisher/test_init_remote.py` (the readings-prerequisites test
  under the new precondition; `test_observed_manual_rows_are_omitted` for the variable dict); `tests/publisher/test_plugin.py` if it lists shipped scripts;
  `openspec/specs/distribution/spec.md` (via the delta);
  `.agent-process/docs/adr/0041-adopters-record-task-readings-in-their-own-stack.md` (D4 points
  to 0048); `skills/agent-process/SKILL.md` (Install step 4);
  `.agent-process/docs/telemetry-measurement-setup.md` (the row text).
- Removed: none. No new dependency: HTTP is `urllib`, as `task_readings.py` already uses.
