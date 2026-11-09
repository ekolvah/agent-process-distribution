## MODIFIED Requirements

### Requirement: Actions credentials are printed, not set
A run SHALL print, as `manual`, setting the repository secret `CLAUDE_CODE_OAUTH_TOKEN` while
the repository's secret names do not include it, and `init` SHALL issue no command that writes
a secret or a variable other than the steps of *Task readings are set up, or printed with the
reason*. The row SHALL name the repository's Actions secrets page and give the commands
`claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`, with the
consumer repository substituted.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository without the secret
- **THEN** its output carries one `manual` row for the secret naming that repository's Actions secrets page, `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` of that repository, and no command it issued writes a secret

#### Scenario: Readings prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository with neither the variable `GRAFANA_URL` nor the secret `GRAFANA_SERVICE_ACCOUNT_TOKEN`, on a machine whose `~/.claude.json` configures no `grafana` MCP server
- **THEN** its output carries one `manual task-readings` row naming that repository's Actions variables page, `gh variable set GRAFANA_URL -R <owner/repo>`, `gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>`, `agent-process dashboard <owner/repo>` of that repository, Grafana's dashboard import and `(not found: grafana MCP server in ~/.claude.json)`, and no command it issued writes a secret or a variable

## ADDED Requirements

### Requirement: Task readings are set up, or printed with the reason
When `~/.claude.json` configures the `grafana` MCP server with `GRAFANA_URL` and a token — its
`GRAFANA_SERVICE_ACCOUNT_TOKEN` or the content of its `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE` — a
run SHALL print the transitions `task-readings-url` (the variable `GRAFANA_URL` set to that
URL), `task-readings-token` (the secret `GRAFANA_SERVICE_ACCOUNT_TOKEN` set to that token) and
`task-readings-dashboard` (the dashboard `agent-process dashboard <owner/repo>` renders, bound
to the stack's datasource of type `yesoreyeram-infinity-datasource`), each `unchanged` when
its state is observed; a confirmed run SHALL perform the planned ones and print the dashboard's
URL. The token SHALL reach `gh` on standard input only and SHALL NOT appear in a command line
or the output. A failed task-readings write SHALL print an error naming its step and exit 1.

A run SHALL plan no task-readings step and send no Grafana request when the repository's
`GRAFANA_URL` names another URL, and no dashboard step when the stack lists no Infinity
datasource or a read of it fails. While the variable, the secret or that dashboard is not set
up and no step sets it up — for another URL, while the secret is missing — the run SHALL print one `manual task-readings` row naming the repository's Actions variables page, the
commands `gh variable set GRAFANA_URL -R <owner/repo>`,
`gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>` and
`agent-process dashboard <owner/repo>` with the consumer repository substituted, and Grafana's
dashboard import, ending with the reason: `(not found: <what>)`, `(another stack: <URL>)` or
`(cannot read: <reason>)`.

#### Scenario: Setup planned from the MCP config
- **WHEN** a dry-run runs on a repository with neither `GRAFANA_URL` nor `GRAFANA_SERVICE_ACCOUNT_TOKEN`, on a machine whose `grafana` MCP server names a URL and a token, and that stack lists an Infinity datasource
- **THEN** it prints `planned task-readings-url` with that URL, `planned task-readings-token` and `planned task-readings-dashboard` with the datasource's uid, issues no write, prints no `manual task-readings` row, and its output and command lines do not contain the token

#### Scenario: Setup performed
- **WHEN** the same run is confirmed, with the token given inline or as a file
- **THEN** the repository's variable `GRAFANA_URL` holds that URL, its secret `GRAFANA_SERVICE_ACCOUNT_TOKEN` was set from standard input with the token, the stack holds the rendered dashboard with no `${DS_INFINITY}` left and the datasource's uid in its place, the output names the dashboard's URL, and no `manual task-readings` row is printed

#### Scenario: Setup observed
- **WHEN** a run meets the variable `GRAFANA_URL` equal to the config's URL, the secret set, and the rendered dashboard's title present in the stack
- **THEN** all three transitions are `unchanged`, it issues no write, and prints no `manual task-readings` row

#### Scenario: Setup not possible
- **WHEN** the repository's `GRAFANA_URL` names another URL and the secret is missing, or the config's stack lists no Infinity datasource, or its read fails
- **THEN** the run exits as it would otherwise, prints no `task-readings-dashboard` transition (and, for another URL, no task-readings transition, no write and no Grafana request), and the `manual task-readings` row ends with `(another stack: <URL>)`, `(not found: Infinity datasource in <URL>)` or `(cannot read: <reason>)`

#### Scenario: Setup write fails
- **WHEN** a confirmed run's `gh secret set` exits non-zero, or its dashboard import is refused by the stack
- **THEN** it prints an error naming `task-readings-token` or `task-readings-dashboard` with the failure, without the token, and exits 1

#### Scenario: Another stack already set
- **WHEN** the repository's `GRAFANA_URL` names another URL and its secret `GRAFANA_SERVICE_ACCOUNT_TOKEN` is set
- **THEN** the run prints no task-readings transition and no `manual task-readings` row
