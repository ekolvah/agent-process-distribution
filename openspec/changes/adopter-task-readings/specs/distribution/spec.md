## RENAMED Requirements

- FROM: `### Requirement: The review secret is printed, not set`
- TO: `### Requirement: Actions credentials are printed, not set`

## MODIFIED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, the managed
`.github/workflows/task-readings.yml`, one marker-owned Dependabot entry, the
marker-owned block of `.pre-commit-config.yaml` — the whole file when the run creates it —, the
seeded `.github/agent-process-quality.json`, the skill
check `.claude/agent-process-check.py`, in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`, and, outside the working tree, the
pre-push hook of this clone that `pre-commit install --hook-type pre-push` writes. Every other
consumer file, key, and hook entry SHALL keep its content, and no publisher file is copied into
the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those nine files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secrets `CLAUDE_CODE_OAUTH_TOKEN` and `GRAFANA_SERVICE_ACCOUNT_TOKEN` and the variable `GRAFANA_URL` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, and a linked public Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`

### Requirement: Actions credentials are printed, not set
A run SHALL print, as `manual`, setting the repository secret `CLAUDE_CODE_OAUTH_TOKEN` while
the repository's secret names do not include it, and `init` SHALL issue no command that writes
a secret or a variable. The row SHALL name the repository's Actions secrets page and give the
commands `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`, with
the consumer repository substituted. A run SHALL print one `manual task-readings` row while the
repository's variable names do not include `GRAFANA_URL` or its secret names do not include
`GRAFANA_SERVICE_ACCOUNT_TOKEN`; the row SHALL name the repository's Actions variables page and
give the commands `gh variable set GRAFANA_URL -R <owner/repo>` and
`gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>`, with the consumer repository
substituted.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository without the secret
- **THEN** its output carries one `manual` row for the secret naming that repository's Actions secrets page, `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` of that repository, and no command it issued writes a secret

#### Scenario: Readings prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository with neither the variable `GRAFANA_URL` nor the secret `GRAFANA_SERVICE_ACCOUNT_TOKEN`
- **THEN** its output carries one `manual task-readings` row naming that repository's Actions variables page, `gh variable set GRAFANA_URL -R <owner/repo>` and `gh secret set GRAFANA_SERVICE_ACCOUNT_TOKEN -R <owner/repo>` of that repository

## ADDED Requirements

### Requirement: The task-readings caller runs at the release tag
The installer SHALL render a managed `.github/workflows/task-readings.yml` whose one job
`task-readings` runs on a closed pull request that was merged and on a `workflow_dispatch`
with a required number input `pr`, and calls
`ekolvah/agent-process-distribution/.github/workflows/reusable-task-readings.yml@v<version>`
with the PR number as `pr`, the repository variable `GRAFANA_URL` as `grafana_url`, and the
repository secret `GRAFANA_SERVICE_ACCOUNT_TOKEN` as `grafana_service_account_token`. This
repository's `task-readings.yml` SHALL call the same callee at `@main` with the same
triggers, inputs and secret.

#### Scenario: Task-readings caller render
- **WHEN** the installer renders the task-readings caller for release `<version>`
- **THEN** its one job `task-readings` calls `reusable-task-readings.yml@v<version>` on a merged pull request and on a dispatch, with exactly the inputs and secrets the callee declares
