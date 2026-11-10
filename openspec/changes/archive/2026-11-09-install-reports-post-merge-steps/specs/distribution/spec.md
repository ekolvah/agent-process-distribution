## ADDED Requirements

### Requirement: Install reports inactive protection
`init` SHALL print a `manual protection` row naming
`agent-process activate_protection --pr <N> --dry-run`, then `--confirm`, unless the
`required_status_checks` rules on the repository's default branch require both
`agent-process / quality` and `agent-review / agent-review`.

#### Scenario: Protection inactive
- **WHEN** a run meets a default branch whose rules do not require both process checks
- **THEN** its output carries one `manual protection` row naming both commands

### Requirement: Install reports a pending agent identity
`init` SHALL print a `manual agent-identity` row unless this clone's
`.claude/settings.local.json` carries `env.GH_TOKEN`. The row SHALL name
`gh auth login -s project,workflow` as the bot, `gh auth switch --user`, and the fix the
session-start identity marker names.

#### Scenario: Identity pending
- **WHEN** a run meets a clone whose settings carry no `env.GH_TOKEN`
- **THEN** its output carries one `manual agent-identity` row naming every command above

### Requirement: Install reports disallowed auto-merge
`init` SHALL print a `manual auto-merge` row naming `gh repo edit --enable-auto-merge` unless
the repository's `allow_auto_merge` is true.

#### Scenario: Auto-merge disallowed
- **WHEN** a run meets a repository whose `allow_auto_merge` is false
- **THEN** its output carries one `manual auto-merge` row naming `gh repo edit --enable-auto-merge`

## MODIFIED Requirements

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secrets `CLAUDE_CODE_OAUTH_TOKEN` and `GRAFANA_SERVICE_ACCOUNT_TOKEN` and the variable `GRAFANA_URL` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, the default branch requiring both process checks, this clone's settings carrying `env.GH_TOKEN`, the repository allowing auto-merge, and a linked public Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`

### Requirement: A Claude session start reports a missing agent identity
The installed skill check SHALL stay silent on the identity only when the session's `GH_TOKEN`
equals `env.GH_TOKEN` of the project's `.claude/settings.local.json`. Otherwise, including when
it cannot read that file, it SHALL exit 0 and add a `systemMessage` for the person and an
`additionalContext` for the agent. Each SHALL name `agent-process agent identity not set`, the
reason, and the fix: `agent-process agent_identity --bot <login> --dry-run`, `--confirm`,
`gh repo edit --enable-auto-merge`, and the restart of Claude Code.

#### Scenario: Identity missing
- **WHEN** a Claude session starts without `GH_TOKEN`, or with a `GH_TOKEN` that the project's settings do not hold
- **THEN** the check exits 0 and its output names `agent-process agent identity not set` and every command of the fix, to the person and to the agent

#### Scenario: Identity set
- **WHEN** a Claude session starts with the `GH_TOKEN` of the project's settings
- **THEN** the check adds nothing for the identity
