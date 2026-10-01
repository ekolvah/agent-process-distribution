## MODIFIED Requirements

### Requirement: Init asks for no quality command
`init` SHALL take no test or setup command. The quality commands of a repository SHALL live in
its own declaration `.github/agent-process-quality.json`, a JSON object with a non-blank string
`test` and optional string `setup` and `checks`, each on one line, which `init` never writes. While that file is
absent or declares no valid `test`, the output of a dry-run and of a confirmed run SHALL carry,
before the `manual` rows, one status line starting `quality: ` that names the declaration and
says CI runs no tests until the declaration exists, and no `manual` row about it. An existing
managed caller that passes a `test` input while the declaration declares no `test` SHALL be
reported as `conflict` naming that input, and the run SHALL exit non-zero before any write.

#### Scenario: Install without tests
- **WHEN** a dry-run or confirmed run meets a repository without `.github/agent-process-quality.json`
- **THEN** its output carries one `quality: ` line naming the declaration before any `manual` row, no `manual quality-command` row, and a confirmed run writes no declaration

#### Scenario: Declared quality command
- **WHEN** a dry-run or confirmed run meets a valid declaration of a `test`
- **THEN** its output carries no `quality: ` line

#### Scenario: Upgrade over a passed test command
- **WHEN** a run meets a managed caller that passes a `test` input and no declaration of a `test`
- **THEN** it prints `conflict` naming the passed command and the declaration file, exits non-zero, and no consumer file has changed

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secret `CLAUDE_CODE_OAUTH_TOKEN` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, and a linked public Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`
