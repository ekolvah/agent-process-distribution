## ADDED Requirements

### Requirement: The marketplace fetches only the package
The installer SHALL render the `agent-process-marketplace` source of `.claude/settings.json`
with `sparsePaths` naming exactly the package directories — `.claude-plugin`, `agents`,
`commands`, and `skills/agent-process` — and this repository's own settings SHALL name the same
list.

#### Scenario: Settings render
- **WHEN** the installer renders the settings of any release, or the publisher tests read this repository's settings
- **THEN** the marketplace source's `sparsePaths` is exactly `.claude-plugin`, `agents`, `commands`, `skills/agent-process`

## MODIFIED Requirements

### Requirement: Confirmation selects the release first
`init --confirm` of a version other than the running installer's SHALL run the requested
release's installer from a temporary checkout of its tag, removed afterwards, before it writes
any consumer file, and the consumer files SHALL be composed by that release's installer from
that release's templates. The running installer SHALL write nothing in the user profile.

#### Scenario: Confirmed upgrade
- **WHEN** an installer of one version runs `--confirm --version` of another version
- **THEN** every consumer write comes from the requested release's installer, and its temporary checkout no longer exists afterwards

#### Scenario: Confirmed install of the running release
- **WHEN** an installer runs `--confirm` of its own version
- **THEN** the user profile is byte-identical before and after

### Requirement: Init fails closed on inputs it does not own
A target the installer does not own — a consumer-owned file or key, or malformed ownership
markers — SHALL be reported as `conflict` and the run SHALL exit non-zero before it writes
any consumer file.

#### Scenario: Target the installer does not own
- **WHEN** a dry-run or confirmed run meets a target the installer does not own
- **THEN** it prints `conflict` for that target, exits non-zero, and no consumer file has changed
