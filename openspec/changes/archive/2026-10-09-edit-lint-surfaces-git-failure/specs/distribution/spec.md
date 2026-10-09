## MODIFIED Requirements

### Requirement: The plugin ships edit-time lint
After an `Edit` or `Write`, the plugin's hook SHALL run `pre-commit run --hook-stage pre-commit
--files <edited path>` in the root of the git repository that holds the edited file, a worktree
being its own root, and SHALL show the agent that run's output with exit 2 when the run fails.
A run that passes SHALL produce no output. A file for which git finds no repository, a file inside a git
directory, or a file in a repository without `.github/workflows/agent-process.yml` SHALL
produce no output. When git fails
for the edited file's directory for any other reason, the hook SHALL exit 2 with a marker saying
that edit-time lint is not active and carrying git's error output. When
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

#### Scenario: Worktree file
- **WHEN** the hook runs with the main checkout of an adopted consumer as its working directory, for a file of a `git worktree` of it, and the consumer's `pre-commit`-stage hook excludes that file's root-relative directory
- **THEN** it exits 0 with no output, and for a file the hook does not exclude it exits 2 with the finding

#### Scenario: Worktree branch config
- **WHEN** the hook runs from the main checkout for a file of a worktree whose branch changed `.pre-commit-config.yaml`
- **THEN** the branch's `pre-commit`-stage hooks run, not the main checkout's

#### Scenario: File outside an adopted repository
- **WHEN** the hook runs from an adopted consumer for a file in no git repository, a file inside a repository's `.git` directory, or a file in a git repository without `.github/workflows/agent-process.yml`
- **THEN** it exits 0 with no output

#### Scenario: Git fails inside a repository
- **WHEN** the hook runs for a file of a git repository that git refuses to read: dubious ownership, an unknown repository extension, or a `.git` file naming a missing git directory
- **THEN** it exits 2 with stderr saying that edit-time lint is not active and carrying git's message

#### Scenario: pre-commit missing
- **WHEN** the hook runs with no `pre-commit` on `PATH`
- **THEN** it exits 2 with stderr naming `pre-commit` and saying that edit-time lint is not active

#### Scenario: This repository's edit-time lint
- **WHEN** the publisher tests read this repository's `.pre-commit-config.yaml`, `.agent-process/requirements-dev.in` and `.claude/settings.json`
- **THEN** the config declares `ruff-check` and `ruff-format` of `astral-sh/ruff-pre-commit` at the `pre-commit` stage only, `requirements-dev.in` names no `ruff`, and the settings declare no `PostToolUse` hook
