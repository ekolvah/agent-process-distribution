## MODIFIED Requirements

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
set, and then `pre-commit install --hook-type pre-push`. When `core.hooksPath` is set and the
hooks directory git uses holds entries other than `*.sample`, the reason SHALL name that
directory and those entries, say that git stops running them once `core.hooksPath` is unset,
and say to port them to `.pre-commit-config.yaml` as `repo: local` hooks first.

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
- **WHEN** a dry-run or confirmed run completes in a clone that has `core.hooksPath` set to a directory that does not exist, or where `pre-commit` is not on `PATH`
- **THEN** it prints no `pre-push` transition, writes no hook, and its output carries one `manual pre-push` row naming that reason and both commands, and no `repo: local`

#### Scenario: Per-clone row over existing hooks
- **WHEN** a dry-run or confirmed run completes in a clone whose `core.hooksPath` directory holds `commit-msg` and `pre-push.sample`
- **THEN** the directory is unchanged, and the one `manual pre-push` row names the directory, `commit-msg`, that git stops running it once `core.hooksPath` is unset, `.pre-commit-config.yaml`, `repo: local` and both commands, and not `pre-push.sample`

### Requirement: A Claude session start reports a missing pre-push hook
When the project directory's `.pre-commit-config.yaml` carries the line `# agent-process:begin`
and this clone has `core.hooksPath` set or has no pre-push hook that pre-commit installed, the
installed skill check SHALL exit 0 with a `systemMessage` for the person and an
`additionalContext` for the agent, each naming `agent-process pre-push hook not installed`, the
reason, `git config --unset-all core.hooksPath` where it is set, and
`pre-commit install --hook-type pre-push`. When `core.hooksPath` is set and the hooks directory
git uses holds entries other than `*.sample`, the reason SHALL name them as the `init` row does.
A state it cannot read SHALL print the same marker naming that reason. Without that line, or
with the hook installed, it SHALL add nothing for the hook; a skill marker it prints SHALL stay
in the same output.

#### Scenario: Hook missing
- **WHEN** a Claude session starts in a clone whose `.pre-commit-config.yaml` carries the agent-process block and that has no pre-push hook pre-commit installed, or has `core.hooksPath` set
- **THEN** the check exits 0 and its output names `agent-process pre-push hook not installed`, the reason, and both commands, to the person and to the agent

#### Scenario: Hook missing over existing hooks
- **WHEN** a Claude session starts in a clone whose `.pre-commit-config.yaml` carries the agent-process block and whose `core.hooksPath` directory holds `commit-msg`
- **THEN** the check's output names the directory, `commit-msg`, that git stops running it once `core.hooksPath` is unset, `.pre-commit-config.yaml` and `repo: local`, to the person and to the agent

#### Scenario: Hook installed or not rendered
- **WHEN** the skill is loaded and the clone's `.pre-commit-config.yaml` has no agent-process block, or the clone runs pre-commit's pre-push hook
- **THEN** the check prints nothing and exits 0

#### Scenario: Hook state unreadable
- **WHEN** the check cannot read `.pre-commit-config.yaml`, the git config, or the hook path
- **THEN** the check exits 0 with the `agent-process pre-push hook not installed` marker naming that reason
