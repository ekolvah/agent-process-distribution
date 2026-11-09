## Context

`init` prints a list of `Step`s (`skills/agent-process/scripts/steps.py`), applies the planned
ones on `--confirm`, then classifies the `manual` rows after the writes (`manual.rows`). The
pre-push hook already has the shape this change needs: one state reader, `manual.pre_push(t) ->
PrePush(…, blocked)`, feeds both the `pre-push` step and the `manual pre-push` row. `init.py` is
at the module-size limit (`max-module-lines = 1000`, `pyproject.toml`). The dashboard command
leaves `${DS_INFINITY}` as a Grafana import input (ADR 0042).

## Standard approach

- Grafana MCP server config: <https://github.com/grafana/mcp-grafana> — its Quick Start
  `mcpServers.grafana.env` holds `GRAFANA_URL` and `GRAFANA_SERVICE_ACCOUNT_TOKEN`; the README
  also names `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE`, the form this machine uses (proposal
  **Why**). Claude Code keeps user-scope MCP servers in `~/.claude.json` `mcpServers`.
- Grafana HTTP API: <https://grafana.com/docs/grafana/latest/developers/http_api/data_source/>
  (`GET /api/datasources`), <https://grafana.com/docs/grafana/latest/developers/http_api/dashboard/>
  (`POST /api/dashboards/db`, which returns the dashboard's `url`),
  <https://grafana.com/docs/grafana/latest/developers/http_api/folder_dashboard_search/>
  (`GET /api/search?type=dash-db&query=…`).
- `gh secret set` <https://cli.github.com/manual/gh_secret_set>: "The value for the secret
  (reads from standard input if not specified)".

## Decisions

- **D1 — the source is the user-scope Grafana MCP config only.** Problem: issue 473. The OTLP
  endpoint names no stack (proposal **Why**). Project-scope MCP entries and `.mcp.json` are not
  read: not observed in use, and without a config today's row stays, so nothing regresses. The
  token is `GRAFANA_SERVICE_ACCOUNT_TOKEN`, else the file's content; both are mcp-grafana's
  documented forms.
- **D2 — the MCP token is copied; no service account is created.** Creating one needs
  `serviceaccounts:create`, which the observed token lacked (`403`). The dry-run's
  `task-readings-token` detail names the source, so the person sees the copy before
  `--confirm`.
- **D3 — steps inside `init`, after the pre-push step.** The `Step` model gives dry-run,
  confirm and `unchanged` as they are; last place means a failed Grafana write cannot stop the
  installation PR. A separate `task_readings_setup` command was rejected: Install would gain a
  step the agent must remember.
- **D4 — one reader, as for pre-push, without an import cycle.** `manual.py` gains, beside
  `pre_push`, the `Grafana` Protocol and `readings(t) -> Readings(url, token, token_source,
  variable, secret, datasource, dashboard, blocked)`; the `manual task-readings` row calls it
  after the writes and prints while `blocked` is set or a name is missing with no config —
  replacing today's `_outstanding` row, so `manual.rows` keeps its signature. New module
  `readings_setup.py` imports `manual`, `dashboard` and `steps` (never the reverse) and holds
  the `urllib` client and `steps(t, readings) -> list[Step]`. `manual.Target` gains
  `grafana: Callable[[str, str], Grafana]` and `gh_write`, a `gh` call with standard input
  that raises `InstallError` on a non-zero exit (`Target.gh` reads and never raises); its one
  constructor, `init._target`, passes both, the factory from `Host`/`Context`, so tests
  inject an in-memory one (§II).
  Line budget of `init.py` (1000 now): `run` moves to `steps.py`, imported back by name so
  `init.run` still resolves (−21); `import readings_setup`, the `Host` and `Context` fields
  and their pass-through, `grafana=` in `_target`, the steps in the run's list, `input` on
  `Context.call`, `gh_write=` (+10) — about 989.
- **D5 — reuse of existing reads.** JSON files (`~/.claude.json`, nothing else) go through
  `manual._plugin_file` (`None` → `not found`, `Unreadable` → `cannot read`); a token file that
  is missing or unreadable is the same. Secret names come from the shared
  `_names_or_unreadable`; the variable read widens `_names` to `--json name,value` (`gh variable list --json` lists
  `createdAt name numSelectedRepos selectedReposURL updatedAt value visibility`, observed
  2026-11-07), so no `gh variable get` is added. Grafana errors raise `manual.Unreadable`, so `_outstanding`-style
  `(cannot read: …)` wording is shared.
- **D6 — read order and observed state.** Variable first: a value other than the config's URL
  is `blocked = "another stack: <value>"` and nothing else is read, so a token never goes to a
  stack the repository does not name; the row then prints only while the secret is missing,
  since a repository with both set records to the stack it chose. Then the dashboard search
  by the render's title, matched exactly: the query matches substrings —
  `GET /api/search?type=dash-db&query=Per-task%20delivery` on this stack returned both
  `Per-task delivery: ekolvah/agent-process-distribution` and
  `Per-task delivery: ekolvah/lampa-mediacenter` (observed 2026-11-07). The render has no
  `uid`. Only when that misses,
  `GET /api/datasources`, keeping the first of type `yesoreyeram-infinity-datasource`.
- **D7 — binding and writing.** The render's `${DS_INFINITY}` is replaced by that uid, then
  `POST /api/dashboards/db` with `overwrite: false` — the path observed in the issue. `apply`
  does not search again. `/api/dashboards/import` with `inputs` would keep ADR 0042's input
  binding but was not observed; probing it would write to a live stack during planning.
- **D8 — failures.** A failed read: no dependent step, the row's reason, exit code unchanged.
  A failed write of a planned step — `gh variable set`, `gh secret set` or the import —
  raises `InstallError` naming the step and the exit status or HTTP status with the first
  line of output, never headers or the token → `error: …`, exit 1 (§III, §IV).

## Risks / Trade-offs

- The repository secret holds the person's MCP token, which may have more than Viewer rights,
  and the repository's workflows can use it. Mitigated by the dry-run naming the copy; the
  person can replace the secret with a Viewer token. Recorded in ADR 0048.
- Title as identity: a renamed dashboard, or one created between the confirm run's search
  and its import, leads to a second import. Accepted.

## Migration / Rollback

No state migration. Adopters that did the row by hand see `unchanged` when their `GRAFANA_URL` equals the
config's byte for byte; otherwise no step and no row, as today. Rollback is the revert
of the PR: `init` prints the row again. ADR 0048 amends ADR 0041 D4.
