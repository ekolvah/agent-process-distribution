## ADDED Requirements

### Requirement: A Claude session start reports release drift
When the project's `openspec/config.yaml` holds the line `# agent-process:begin`, the plugin's
`SessionStart` hook SHALL compare the recorded release with its own as `start_change` does and,
on drift, exit 0 with a `systemMessage` for the person and an `additionalContext` for the agent,
each naming `agent-process release drift`, both releases and the fix for that direction, which
for a recorded release that is absent, unparsable or older is `/agent-process:init`. A config it
cannot read SHALL print the same marker naming that reason. Without that line or that file, or
with equal releases, it SHALL add nothing for the release.

#### Scenario: Repository behind the plugin
- **WHEN** a Claude session starts in a project whose config block records `3.29.0` and the plugin is a later release
- **THEN** the hook exits 0 and its output names `agent-process release drift`, both releases and `/agent-process:init`, to the person and to the agent

#### Scenario: Release current or not installed
- **WHEN** the config block records the plugin's release, or the config holds no agent-process block, or there is no config
- **THEN** the hook adds nothing for the release

#### Scenario: Release undecidable
- **WHEN** the project's `openspec/config.yaml` cannot be read
- **THEN** the hook exits 0 and its output names `agent-process release drift` and `cannot check`

## MODIFIED Requirements

### Requirement: Delivery entry scripts refuse release drift
The installer SHALL record the installed release as the line `# agent-process release: <version>`
in its `openspec/config.yaml` block. `finish_propose` and `start_change` SHALL read that
line before any other step and, when it is absent, not a `<major>.<minor>.<patch>` version, or
different from the release of the running skill, exit 2 without a GitHub call, naming both
releases and the fix: re-run Install with the running skill (`/agent-process:init`) when the
project's release is absent, unparsable or older, or `claude plugin update
agent-process@agent-process-marketplace` with the install's scope and a session restart when the
skill's release is older, never a marketplace ref pinned to a release tag. Scripts run from
`skills/agent-process/scripts` under the repository root SHALL skip the comparison.

#### Scenario: Release recorded
- **WHEN** a confirmed installer run writes the `openspec/config.yaml` block
- **THEN** the block holds `# agent-process release: <version>` of the installed release

#### Scenario: Release drift
- **WHEN** `finish_propose` or `start_change` runs from a skill outside the repository's `skills/agent-process/scripts` and the recorded release is absent, unparsable, older or newer than the skill's
- **THEN** it exits 2 before any GitHub call, and its message names both releases and the fix for that direction, `/agent-process:init` for an absent, unparsable or older project release

#### Scenario: Publisher checkout
- **WHEN** either script runs from `<root>/skills/agent-process/scripts` of a repository whose config records no release
- **THEN** it proceeds past the comparison
