## ADDED Requirements

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secret `CLAUDE_CODE_OAUTH_TOKEN` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, and a linked public Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row other than `quality-command`

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`

## MODIFIED Requirements

### Requirement: Project UI actions are printed, not performed
A run SHALL print, as `manual`, setting the Project's visibility while the linked Project is
private, enabling the template's built-in workflows the linked Project lacks or has disabled —
naming only those — and replacing the `Area` options and area views with the consumer's own
while the linked Project's `Area` options equal the template's; and `init` SHALL issue no
command that changes any of them.

#### Scenario: Manual actions
- **WHEN** a confirmed run completes after copying and linking the template Project
- **THEN** its output carries the three `manual` rows, the workflows row names `Auto-add to project` and no other workflow, and no command it issued changes a Project's visibility, workflows, fields or views

### Requirement: The review secret is printed, not set
A run SHALL print, as `manual`, setting the repository secret `CLAUDE_CODE_OAUTH_TOKEN` while
the repository's secret names do not include it, and `init` SHALL issue no command that writes
a secret.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository without the secret
- **THEN** its output carries one `manual` row for the secret, and no command it issued writes a secret

### Requirement: The marketplace follows the stable channel
The installer SHALL render the `agent-process-marketplace` declaration of
`.claude/settings.json` with the source `ref` `stable` and `"autoUpdate": true`, for every
release. A run SHALL print, as `manual`, the once-per-machine step that declares the
marketplace at `stable` in user settings, enables its auto-update, and installs the plugin at
user scope, while the machine's known marketplace is not at `stable` with auto-update or the
plugin has no user-scope install, and `init` SHALL issue no command that changes plugin or
marketplace state.

#### Scenario: Channel render
- **WHEN** the installer renders the settings of any release
- **THEN** the marketplace source's `ref` is `stable` and the marketplace entry's `autoUpdate` is `true`

#### Scenario: Machine channel step
- **WHEN** a dry-run or confirmed run completes on a machine without the marketplace
- **THEN** its output carries one `manual plugin-channel` row naming `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`, enabling auto-update, and `claude plugin install agent-process@agent-process-marketplace`, and no command it issued is a `claude` command

### Requirement: Init renders the pre-push hook
The owned block of `.pre-commit-config.yaml` SHALL reference the hook `quality` of
`https://github.com/ekolvah/agent-process-distribution` at `rev: v<version>`, and a file the run
creates SHALL also set `default_install_hook_types: [pre-push]`. An existing file without the
block SHALL be reported as `conflict`. A run SHALL print a `manual pre-push` row naming, per
clone, `git config --unset-all core.hooksPath` where it is set and then
`pre-commit install --hook-type pre-push`, while this clone has `core.hooksPath` set or its
pre-push hook is not one pre-commit installed.

#### Scenario: Consumer render
- **WHEN** a confirmed run installs release `<version>`
- **THEN** `.pre-commit-config.yaml` references the hook `quality` at `rev: v<version>`, and pre-commit runs it at `pre-push`

#### Scenario: Consumer file without the block
- **WHEN** a run meets a `.pre-commit-config.yaml` without an agent-process block
- **THEN** it prints `conflict` for that file, exits non-zero, and no consumer file has changed

#### Scenario: Per-clone row
- **WHEN** a dry-run or confirmed run completes in a clone without a pre-push hook
- **THEN** its output carries one `manual pre-push` row naming both commands
