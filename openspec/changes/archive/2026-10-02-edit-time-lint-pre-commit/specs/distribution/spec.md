## ADDED Requirements

### Requirement: The plugin ships edit-time lint
After an `Edit` or `Write`, the plugin's hook SHALL run `pre-commit run --hook-stage pre-commit
--files <edited path>` in the session's project directory and SHALL show the agent that run's
output with exit 2 when the run fails. A run that passes SHALL produce no output. When
`pre-commit` is not on `PATH`, the hook SHALL exit 2 with a marker saying that edit-time lint is
not active. This repository's `.pre-commit-config.yaml` SHALL
declare the `ruff-check` and `ruff-format` hooks of `astral-sh/ruff-pre-commit` at the
`pre-commit` stage as its only pin of ruff, and its `.claude/settings.json` SHALL declare no
`PostToolUse` hook.

#### Scenario: Commit-stage finding
- **WHEN** the plugin's hook runs in an adopted consumer whose `.pre-commit-config.yaml` declares a `pre-commit`-stage hook that fails on the edited file
- **THEN** it exits 2 with stderr carrying that hook's output

#### Scenario: Only pre-push hooks declared
- **WHEN** the same hook runs in an adopted consumer whose `.pre-commit-config.yaml` declares hooks only at the `pre-push` stage
- **THEN** it exits 0 with no output, and no `pre-push` hook runs

#### Scenario: pre-commit missing
- **WHEN** the hook runs with no `pre-commit` on `PATH`
- **THEN** it exits 2 with stderr naming `pre-commit` and saying that edit-time lint is not active

#### Scenario: This repository's edit-time lint
- **WHEN** the publisher tests read this repository's `.pre-commit-config.yaml`, `.agent-process/requirements-dev.in` and `.claude/settings.json`
- **THEN** the config declares `ruff-check` and `ruff-format` of `astral-sh/ruff-pre-commit` at the `pre-commit` stage only, `requirements-dev.in` names no `ruff`, and the settings declare no `PostToolUse` hook

## MODIFIED Requirements

### Requirement: The plugin ships the memory checkpoint
After an `Edit` or `Write` of a file under the agent's auto-memory directory
(`.claude/projects/<project>/memory/`), the plugin's hook SHALL show the agent a reminder
without undoing the write. The reminder SHALL name the file and ask whether every session and
every person working on the repository needs the fact; if so, it SHALL ask the agent to move
the fact into the repository. Any
other path SHALL produce no output. This repository's `.claude/settings.json` SHALL declare no
post-edit hook of its own.

#### Scenario: Memory write in an adopted consumer
- **WHEN** the plugin's `PostToolUse` hook runs with a project directory that carries `.github/workflows/agent-process.yml` and no copy of the check, for a `Write` of a file under `.claude/projects/<project>/memory/` given with either path separator
- **THEN** it exits 2 with stderr naming the file, asking whether every session and every person needs the fact, and if so to move it into the repository

#### Scenario: Write outside auto-memory
- **WHEN** the same hook runs for a file of the repository, including one under `.claude/rules/`, or for a payload without a file path
- **THEN** it exits 0 with no output

#### Scenario: Repository hook carries no memory check
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** it declares no `PostToolUse` hook, so the plugin's checkpoint is the only memory check
