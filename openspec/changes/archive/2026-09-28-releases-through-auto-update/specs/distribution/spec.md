## ADDED Requirements

### Requirement: The marketplace follows the stable channel
The installer SHALL render the `agent-process-marketplace` declaration of
`.claude/settings.json` with the source `ref` `stable` and `"autoUpdate": true`, for every
release. The plan of a dry-run and of a confirmed run SHALL print, as `manual`, the once-per-machine
step that declares the marketplace at `stable` in user settings and enables its auto-update,
and `init` SHALL issue no command that changes plugin or marketplace state.

#### Scenario: Channel render
- **WHEN** the installer renders the settings of any release
- **THEN** the marketplace source's `ref` is `stable` and the marketplace entry's `autoUpdate` is `true`

#### Scenario: Machine channel step
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries one `manual plugin-channel` row naming `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"` and enabling auto-update, and no command it issued is a `claude` command

### Requirement: A release moves the stable channel
When the release workflow creates a release, it SHALL fast-forward the branch `stable` to the
commit that release tagged, with the token that tagged it. A failed or non-fast-forward update
SHALL fail the workflow run. A run that creates no release SHALL NOT change `stable`.

#### Scenario: Release created
- **WHEN** the release workflow creates the release of version `<version>`
- **THEN** it updates `refs/heads/stable` to the tagged commit without force, and a refused update fails the run

#### Scenario: No release
- **WHEN** the release workflow runs and creates no release
- **THEN** the `stable` update step is skipped

### Requirement: Dependabot leaves process refs to Install
The installer's marker-owned Dependabot entry SHALL ignore every dependency named
`ekolvah/agent-process-distribution` or under it.

#### Scenario: Dependabot render
- **WHEN** the installer writes its Dependabot entry
- **THEN** the `github-actions` entry ignores the dependency name pattern `ekolvah/agent-process-distribution*`

## MODIFIED Requirements

### Requirement: Delivery entry scripts refuse release drift
The installer SHALL record the installed release as the line `# agent-process release: <version>`
in its `openspec/config.yaml` block. `create_tracking_issue` and `start_change` SHALL read that
line before any other step and, when it is absent, not a `<major>.<minor>.<patch>` version, or
different from the release of the running skill, exit 2 without a GitHub call, naming both
releases and the fix: re-run Install with the running skill when the project's release is absent,
unparsable or older, or `claude plugin update agent-process@agent-process-marketplace` with the
install's scope and a session restart when the skill's release is older, never a marketplace ref pinned to a release
tag. Scripts run from `skills/agent-process/scripts` under the repository root SHALL skip the
comparison.

#### Scenario: Release recorded
- **WHEN** a confirmed installer run writes the `openspec/config.yaml` block
- **THEN** the block holds `# agent-process release: <version>` of the installed release

#### Scenario: Release drift
- **WHEN** `create_tracking_issue` or `start_change` runs from a skill outside the repository's `skills/agent-process/scripts` and the recorded release is absent, unparsable, older or newer than the skill's
- **THEN** it exits 2 before any GitHub call, and its message names both releases and the fix for that direction

#### Scenario: Publisher checkout
- **WHEN** either script runs from `<root>/skills/agent-process/scripts` of a repository whose config records no release
- **THEN** it proceeds past the comparison
