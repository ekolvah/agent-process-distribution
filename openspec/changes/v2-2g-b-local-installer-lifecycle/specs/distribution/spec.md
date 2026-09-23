## ADDED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, one
marker-owned Dependabot entry, and two keys of `.claude/settings.json`. Every other consumer
file and key SHALL keep its content, and no publisher file is copied into the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those four files, and only the two owned settings keys are added

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release and consumer content beside it
- **THEN** only the owned block, file, and keys change, and every consumer byte outside them is identical

### Requirement: Init previews the requested release
`init --dry-run` SHALL print the plan of the requested release, one line per transition
marked `planned`, `unchanged`, or `conflict`, and SHALL leave no persistent state in the
consumer repository or the user profile. When the requested version differs from the
running installer's, the plan, its output, and its exit code SHALL come from the requested
release's own installer, run from a temporary checkout that is removed afterwards.

#### Scenario: Dry-run of another version
- **WHEN** an installer of one version runs `--dry-run --version` of another version
- **THEN** the output and exit code are the requested release's own dry-run, and the consumer repository and user profile are byte-identical before and after

### Requirement: Confirmation selects the release first
`init --confirm` SHALL move the user-scope Codex checkout to the requested release before it
writes any consumer file, and the consumer files SHALL be composed by that release's
installer from that release's templates.

#### Scenario: Confirmed upgrade
- **WHEN** an installer of one version runs `--confirm --version` of another version
- **THEN** the checkout is at the requested tag before the first consumer write, and every consumer write comes from the requested release's installer

### Requirement: The Codex skill links the selected release
After a confirmed run, `~/.agents/skills/agent-process` SHALL resolve to the
`skills/agent-process` directory of the process checkout at the requested tag: a directory
junction on Windows and a symbolic link on Unix.

#### Scenario: Link on Windows and Unix
- **WHEN** a confirmed run completes on Windows or on Unix
- **THEN** the user skill path resolves to the checkout's skill directory at the requested tag

### Requirement: Init reconciles from observable state
Each transition SHALL be decided from the state it observes, so a rerun of the same version
writes nothing and a retry after an interrupted run performs every unfinished transition
exactly once and no completed one again.

#### Scenario: Retry after an interrupted write
- **WHEN** a confirmed run stops after any one of its persistent writes and is run again
- **THEN** the retry reports each completed transition `unchanged`, performs each unfinished one once, and ends in the same state as an uninterrupted run

### Requirement: Init fails closed on inputs it does not own
A target the installer does not own — a consumer-owned file or key, malformed ownership
markers, a checkout that is dirty or has another origin, or a user skill path that is not
its link — SHALL be reported as `conflict` and the run SHALL exit non-zero before it writes
any consumer file. A user-profile conflict SHALL be found before any user-profile write.

#### Scenario: Target the installer does not own
- **WHEN** a dry-run or confirmed run meets a target the installer does not own
- **THEN** it prints `conflict` for that target, exits non-zero, and no consumer file has changed

### Requirement: Local installation writes nothing remote
The installer's local lifecycle SHALL NOT create, update, or delete a GitHub Project,
ruleset, branch protection, required check, or secret, and SHALL NOT commit or push in the
consumer repository.

#### Scenario: Confirmed run
- **WHEN** a confirmed run completes
- **THEN** it has issued no GitHub API or `gh` command and no commit or push, and the consumer's changes are left uncommitted in its worktree

## MODIFIED Requirements

### Requirement: This repository dogfoods its own process
This repository SHALL expose and enable the shared Claude plugin/skill package that its
installer installs in consumers. Repository sessions and publisher tests SHALL exercise the
shared skill source, its portable scripts, its installer and templates, its OpenSpec rule
pointers, and its package-version identity. Repository-only settings and v1 process files
SHALL NOT be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, the installer or a template, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its delivery gates remain intact

## REMOVED Requirements

### Requirement: The process footprint is one root plus a closed exception set
**Reason**: It describes the Copier render deleted by `v2-0b-delete-copier-mirror`; ADR 0027 schedules its restatement together with `init`.
**Migration**: `The installed footprint is closed` states what `init` may change in a consumer.
