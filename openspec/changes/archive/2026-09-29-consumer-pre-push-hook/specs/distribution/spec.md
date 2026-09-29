## MODIFIED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, one marker-owned Dependabot entry, the
marker-owned block of `.pre-commit-config.yaml`, the skill
check `.claude/agent-process-check.py`, and in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`. Every other consumer file, key, and hook entry SHALL keep its content, and
no publisher file is copied into the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those seven files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical

## ADDED Requirements

### Requirement: A push runs the declared test
The pre-commit hook `quality` that this repository's `.pre-commit-hooks.yaml` declares SHALL run
at `pre-push` the `test` that `.github/agent-process-quality.json` of the pushed checkout
declares, once, through `bash`, with the names that `git rev-parse --local-env-vars` prints
and the environment pre-commit built for the hook removed from its environment, and SHALL exit
with that command's exit code. It SHALL run no
`setup` and no `checks`. Without the file it SHALL print that no quality command is declared and
the push checked nothing, and exit 0. A malformed declaration SHALL fail with an error naming the
fault. When `bash` or the git environment names cannot be found it SHALL exit 2 naming the
cause. This repository's `.pre-commit-config.yaml` SHALL run the same entry from its own commit.

#### Scenario: Declared test fails
- **WHEN** the declared `test` exits non-zero
- **THEN** the hook exits with that code and the push is refused

#### Scenario: No declaration
- **WHEN** the pushed checkout has no `.github/agent-process-quality.json`
- **THEN** the hook prints that no quality command is declared and exits 0

#### Scenario: Push from a linked worktree
- **WHEN** the hook runs with `GIT_DIR` and `GIT_INDEX_FILE` set
- **THEN** the declared `test` sees neither

#### Scenario: Declared test runs python
- **WHEN** pre-commit runs the hook and the declared `test` runs `python`
- **THEN** that is the interpreter the pusher's `PATH` names, not the hook's environment

#### Scenario: This repository's push
- **WHEN** this repository's `.pre-commit-config.yaml` is read
- **THEN** its hook `quality` runs `skills/agent-process/scripts/quality.py --hook` at `pre-push`

### Requirement: Init renders the pre-push hook
The owned block of `.pre-commit-config.yaml` SHALL reference the hook `quality` of
`https://github.com/ekolvah/agent-process-distribution` at `rev: v<version>`, and a file the run
creates SHALL also set `default_install_hook_types: [pre-push]`. An existing file without the
block SHALL be reported as `conflict`. The plan of a dry-run and of a confirmed run SHALL print a
`manual pre-push` row naming, per clone, `git config --unset-all core.hooksPath` where it is set
and then `pre-commit install --hook-type pre-push`.

#### Scenario: Consumer render
- **WHEN** a confirmed run installs release `<version>`
- **THEN** `.pre-commit-config.yaml` references the hook `quality` at `rev: v<version>`, and pre-commit runs it at `pre-push`

#### Scenario: Consumer file without the block
- **WHEN** a run meets a `.pre-commit-config.yaml` without an agent-process block
- **THEN** it prints `conflict` for that file, exits non-zero, and no consumer file has changed

#### Scenario: Per-clone row
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries one `manual pre-push` row naming both commands
