## ADDED Requirements

### Requirement: Skill commands run from a consumer root
Every script command a skill file prints SHALL be `agent-process <script>` followed by its
arguments, naming a script of the skill directory. The plugin SHALL ship `agent-process` as an
executable of its `bin/`, which SHALL run `python <script>.py` with the remaining arguments from
`skills/agent-process/scripts/` of the current directory when that file exists there, otherwise
from the plugin's own skill directory, and SHALL propagate the script's exit code. A missing or
unknown script name SHALL exit 2 naming the available scripts.

#### Scenario: Printed command in a consumer
- **WHEN** a command printed by a skill file runs through `agent-process` from a directory that has no `skills/agent-process/`
- **THEN** the named script of the plugin's skill directory runs with the printed arguments and its exit code is the command's

#### Scenario: Publisher checkout runs its own scripts
- **WHEN** `agent-process <script>` runs from a directory whose `skills/agent-process/scripts/<script>.py` exists
- **THEN** that file runs, not the plugin's copy

#### Scenario: Unknown script
- **WHEN** `agent-process` runs without a script name or with a name that is not a script of the skill directory
- **THEN** it exits 2 naming the available scripts and runs nothing

### Requirement: The plugin's component roots are closed
The plugin component roots at the top level of this repository — the default locations the
plugin reference lists: `.claude-plugin`, `skills/<name>`, a root `SKILL.md`, `commands`,
`agents`, `hooks`, `.mcp.json`, `.lsp.json`, `output-styles`, `workflows`, `themes`, `monitors`,
`bin`, and a root `settings.json` — SHALL be exactly `.claude-plugin`, `agents`, `bin`,
`commands`, and `skills/agent-process`. The installer SHALL render the `agent-process-marketplace`
source of `.claude/settings.json` without `sparsePaths`, and this repository's own settings SHALL
name none.

#### Scenario: Component roots
- **WHEN** the publisher tests read the top level of this repository
- **THEN** the component roots present are exactly `.claude-plugin`, `agents`, `bin`, `commands`, `skills/agent-process`, and any other fails naming it

#### Scenario: Settings render
- **WHEN** the installer renders the settings of any release, or the publisher tests read this repository's settings
- **THEN** the marketplace source has no `sparsePaths`

## REMOVED Requirements

### Requirement: The marketplace fetches only the package
**Reason**: A sparse set is frozen on every machine that cloned with it (#184), so a new component root (`bin/`) misses those machines, and the `plugin-channel` row already adds the marketplace whole; the plugin loader reads only component roots, which the closed list now guards.
**Migration**: A consumer's re-run Install renders the marketplace source without `sparsePaths`. A machine whose marketplace was added sparse keeps that set (#184) and fails visibly with `command not found`; removing and adding the marketplace again is the expected recovery, inferred and not yet observed (design.md, Risks).
