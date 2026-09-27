## MODIFIED Requirements

### Requirement: Confirmation selects the release first
`init --confirm` SHALL move the user-scope process checkout to the requested release before it
writes any consumer file, and the consumer files SHALL be composed by that release's
installer from that release's templates.

#### Scenario: Confirmed upgrade
- **WHEN** an installer of one version runs `--confirm --version` of another version
- **THEN** the checkout is at the requested tag before the first consumer write, and every consumer write comes from the requested release's installer

### Requirement: Init fails closed on inputs it does not own
A target the installer does not own — a consumer-owned file or key, malformed ownership markers, or a checkout that is dirty or has another origin — SHALL be reported as `conflict` and the run SHALL exit non-zero before it writes
any consumer file. A user-profile conflict SHALL be found before any user-profile write.

#### Scenario: Target the installer does not own
- **WHEN** a dry-run or confirmed run meets a target the installer does not own
- **THEN** it prints `conflict` for that target, exits non-zero, and no consumer file has changed

### Requirement: Delivery entry scripts refuse release drift
The installer SHALL record the installed release as the line `# agent-process release: <version>`
in its `openspec/config.yaml` block. `create_tracking_issue` and `start_change` SHALL read that
line before any other step and, when it is absent, not a `<major>.<minor>.<patch>` version, or
different from the release of the running skill, exit 2 without a GitHub call, naming both
releases and the fix: re-run Install with the running skill when the project's release is absent,
unparsable or older, or update the plugin and restart the session when the
skill's release is older. Scripts run from `skills/agent-process/scripts` under the repository
root SHALL skip the comparison.

#### Scenario: Release recorded
- **WHEN** a confirmed installer run writes the `openspec/config.yaml` block
- **THEN** the block holds `# agent-process release: <version>` of the installed release

#### Scenario: Release drift
- **WHEN** `create_tracking_issue` or `start_change` runs from a skill outside the repository's `skills/agent-process/scripts` and the recorded release is absent, unparsable, older or newer than the skill's
- **THEN** it exits 2 before any GitHub call, and its message names both releases and the fix for that direction

#### Scenario: Publisher checkout
- **WHEN** either script runs from `<root>/skills/agent-process/scripts` of a repository whose config records no release
- **THEN** it proceeds past the comparison

## REMOVED Requirements

### Requirement: The Codex skill links the selected release
**Reason**: Codex left the process (decided 2026-09-27); no user-wide Codex skill is loaded.
**Migration**: an existing `~/.agents/skills/agent-process` link is left in place; the person deletes it.
