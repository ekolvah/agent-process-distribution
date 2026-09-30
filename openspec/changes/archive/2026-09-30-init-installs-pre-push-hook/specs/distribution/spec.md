## MODIFIED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, one marker-owned Dependabot entry, the
marker-owned block of `.pre-commit-config.yaml`, the skill
check `.claude/agent-process-check.py`, in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`, and, outside the working tree, the
pre-push hook of this clone that `pre-commit install --hook-type pre-push` writes. Every other
consumer file, key, and hook entry SHALL keep its content, and no publisher file is copied into
the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those seven files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical

### Requirement: Init renders the pre-push hook
The owned block of `.pre-commit-config.yaml` SHALL reference the hook `quality` of
`https://github.com/ekolvah/agent-process-distribution` at `rev: v<version>`, and a file the run
creates SHALL also set `default_install_hook_types: [pre-push]`. An existing file without the
block SHALL be reported as `conflict`. A run SHALL classify a `pre-push` transition, printed
after every onboarding transition: `unchanged` while this clone has `core.hooksPath` unset and a
pre-push hook that pre-commit installed, otherwise `planned` when `core.hooksPath` is unset and
`pre-commit` is on `PATH`. A confirmed run SHALL perform it after the installation PR by running
`pre-commit install --hook-type pre-push` in the clone, and SHALL fail with exit 1 when the hook
it then reads is not one pre-commit installed. A planned `pre-push` transition alone SHALL NOT
make a branch, commit, issue, push, or PR. When this clone has `core.hooksPath` set or
`pre-commit` is not on `PATH`, the run SHALL print no `pre-push` transition and SHALL print a
`manual pre-push` row naming that reason, `git config --unset-all core.hooksPath` where it is
set, and then `pre-commit install --hook-type pre-push`.

#### Scenario: Consumer render
- **WHEN** a confirmed run installs release `<version>`
- **THEN** `.pre-commit-config.yaml` references the hook `quality` at `rev: v<version>`, and pre-commit runs it at `pre-push`

#### Scenario: Consumer file without the block
- **WHEN** a run meets a `.pre-commit-config.yaml` without an agent-process block
- **THEN** it prints `conflict` for that file, exits non-zero, and no consumer file has changed

#### Scenario: Hook installed in this clone
- **WHEN** a dry-run and then a confirmed run complete in a clone without a pre-push hook, with `core.hooksPath` unset and `pre-commit` on `PATH`
- **THEN** the dry-run prints `planned pre-push` and leaves the clone without a hook, the confirmed run prints `written pre-push` after `onboarding-pr` and leaves a hook that pre-commit installed, and neither prints a `manual pre-push` row

#### Scenario: Install leaves no hook
- **WHEN** a confirmed run's `pre-commit install --hook-type pre-push` exits 0 but leaves no hook that pre-commit installed
- **THEN** the run prints no `written pre-push`, names the hook path, and exits 1

#### Scenario: Hook missing where nothing else is planned
- **WHEN** a confirmed run on the default branch changes no consumer file in a clone without a pre-push hook, with `core.hooksPath` unset and `pre-commit` on `PATH`
- **THEN** it prints `written pre-push`, and creates no branch, commit, issue, push, or PR

#### Scenario: Per-clone row
- **WHEN** a dry-run or confirmed run completes in a clone that has `core.hooksPath` set, or where `pre-commit` is not on `PATH`
- **THEN** it prints no `pre-push` transition, writes no hook, and its output carries one `manual pre-push` row naming that reason and both commands

## ADDED Requirements

### Requirement: A Claude session start reports a missing pre-push hook
When the project directory's `.pre-commit-config.yaml` carries the line `# agent-process:begin`
and this clone has `core.hooksPath` set or has no pre-push hook that pre-commit installed, the
installed skill check SHALL exit 0 with a `systemMessage` for the person and an
`additionalContext` for the agent, each naming `agent-process pre-push hook not installed`, the
reason, `git config --unset-all core.hooksPath` where it is set, and
`pre-commit install --hook-type pre-push`. A state it cannot read SHALL print the same marker
naming that reason. Without that line, or with the hook installed, it SHALL add nothing for the
hook; a skill marker it prints SHALL stay in the same output.

#### Scenario: Hook missing
- **WHEN** a Claude session starts in a clone whose `.pre-commit-config.yaml` carries the agent-process block and that has no pre-push hook pre-commit installed, or has `core.hooksPath` set
- **THEN** the check exits 0 and its output names `agent-process pre-push hook not installed`, the reason, and both commands, to the person and to the agent

#### Scenario: Hook installed or not rendered
- **WHEN** the skill is loaded and the clone's `.pre-commit-config.yaml` has no agent-process block, or the clone runs pre-commit's pre-push hook
- **THEN** the check prints nothing and exits 0

#### Scenario: Hook state unreadable
- **WHEN** the check cannot read `.pre-commit-config.yaml`, the git config, or the hook path
- **THEN** the check exits 0 with the `agent-process pre-push hook not installed` marker naming that reason
