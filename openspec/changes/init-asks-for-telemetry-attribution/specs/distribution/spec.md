## ADDED Requirements

### Requirement: Init writes the telemetry attribution
`init` SHALL set `env.OTEL_RESOURCE_ATTRIBUTES` of the consumer's `.claude/settings.json` to
`vcs.repository.name=<owner/repo>,vcs.repository.url.full=https://github.com/<owner/repo>`,
with the consumer repository substituted, when that file is absent, or is in the form `init`
writes and sets no such variable, and neither `init`'s environment nor `env` of
`~/.claude/settings.json` sets that variable. Otherwise, while the file's value, read as comma-joined
`key=value` pairs, carries no pair `vcs.repository.name=<owner/repo>`, a run SHALL print, as
`manual telemetry-attribution`, that value, that the settings value replaces the machine's
value of that variable, and the reason `init` did not write it.

#### Scenario: Attribution written
- **WHEN** a dry-run and then a confirmed run complete on a consumer whose `.claude/settings.json` sets no `env.OTEL_RESOURCE_ATTRIBUTES`, on a machine that sets none
- **THEN** the dry-run leaves the file unchanged, the confirmed run leaves it carrying the value of that repository, and neither prints a `manual telemetry-attribution` row

#### Scenario: Machine attribution kept
- **WHEN** a confirmed run completes on such a consumer while `init`'s environment sets `OTEL_RESOURCE_ATTRIBUTES=team=media`
- **THEN** the file carries no `env.OTEL_RESOURCE_ATTRIBUTES` after the run, and its output carries one `manual telemetry-attribution` row naming the value of that repository, `replaces` and `team=media`

#### Scenario: Another repository's attribution
- **WHEN** a run completes on a consumer whose `env.OTEL_RESOURCE_ATTRIBUTES` carries `vcs.repository.name` of another repository
- **THEN** the file's value is unchanged, and its output carries the `manual telemetry-attribution` row

#### Scenario: Settings in another form
- **WHEN** a run completes on a consumer whose `.claude/settings.json` needs no other change from `init` and is not in the form `init` writes
- **THEN** its `settings` step is unchanged, and its output carries the `manual telemetry-attribution` row naming that form as the reason

## MODIFIED Requirements

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secrets `CLAUDE_CODE_OAUTH_TOKEN` and `GRAFANA_SERVICE_ACCOUNT_TOKEN` and the variable `GRAFANA_URL` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, the default branch requiring both process checks, this clone's settings carrying `env.GH_TOKEN`, the consumer's `.claude/settings.json` carrying `vcs.repository.name=<owner/repo>` among other pairs of `env.OTEL_RESOURCE_ATTRIBUTES`, the repository allowing auto-merge, and a linked private Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads, or the consumer's `.claude/settings.json` is not JSON, its `env` is not an object, or its `env.OTEL_RESOURCE_ATTRIBUTES` is not a string
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`
