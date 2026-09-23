# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
The reusable quality workflow SHALL execute the process driver from the trusted default
branch against the PR worktree, so a PR cannot change what checks it.

#### Scenario: Quality check on a PR
- **WHEN** the quality workflow runs for a PR
- **THEN** the driver comes from the default branch and the PR's files are only its input

### Requirement: This repository dogfoods its own process
This repository SHALL expose and enable the shared Claude plugin/skill package that its
installer installs in consumers. Repository sessions and publisher tests SHALL exercise the
shared skill source, its portable scripts, its installer and templates, its OpenSpec rule
pointers, and its package-version identity. Repository-only settings and v1 process files
SHALL NOT be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, the installer or a template, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its delivery gates remain intact

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

### Requirement: Init writes only the Project remotely
A confirmed run's only GitHub writes SHALL be one copy of the template Project and one link
of a Project to the repository. The installer SHALL NOT create, update, or delete a ruleset,
branch protection, required check, secret, Project field or Status, or a workflow on the
default branch, and SHALL NOT commit or push in the consumer repository. A dry-run SHALL
issue no GitHub write.

#### Scenario: Confirmed run
- **WHEN** a confirmed run completes
- **THEN** every GitHub command it issued is a read, the Project copy, or the Project link, it has made no commit or push, and the consumer's changes are left uncommitted in its worktree

#### Scenario: Dry-run
- **WHEN** a dry-run completes
- **THEN** every GitHub command it issued is a read

### Requirement: Init provisions one linked Project
A confirmed run SHALL end with exactly one Project linked to the repository. It SHALL reuse
a Project already linked; otherwise reuse the one open, unlinked Project of the repository's
owner titled `<repository name> agent process`; otherwise copy the template Project under
that title; and then link it. Several linked Projects, several such candidates, or a
same-titled Project that is closed or linked elsewhere when no candidate is reusable SHALL be
reported as `conflict`, and the run SHALL exit non-zero before its first write.

#### Scenario: No Project yet
- **WHEN** a confirmed run meets a repository with no linked Project and no same-titled Project of its owner
- **THEN** it copies the template once under the repository's title and links that copy

#### Scenario: Unlinked copy exists
- **WHEN** no Project is linked and exactly one open, unlinked same-titled Project exists
- **THEN** the run links it and copies nothing

#### Scenario: Ambiguous Projects
- **WHEN** several Projects are linked, several same-titled candidates exist, or the only same-titled Project is closed or linked elsewhere
- **THEN** a dry-run or confirmed run prints `conflict` naming them, exits non-zero, and has written nothing locally or remotely

### Requirement: Project provisioning is recoverable
A retry after a copy or link that failed, or that took effect while its command reported
failure, SHALL decide from the observed Projects and SHALL NOT create a second copy.

#### Scenario: Link failed after the copy
- **WHEN** the copy succeeds, the link fails, and the run is repeated
- **THEN** across both runs the template is copied once and the link is attempted twice, and the copy ends linked

#### Scenario: Link output lost
- **WHEN** the link takes effect but its command reports failure, and the run is repeated
- **THEN** the retry reports the Project linked as `unchanged` and issues no copy and no link

### Requirement: Project UI actions are printed, not performed
The plan of a dry-run and of a confirmed run SHALL print, as `manual`, setting the Project's
visibility and checking the template's built-in workflows, and `init` SHALL issue no command
that changes either.

#### Scenario: Manual actions
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries the two `manual` rows and no command it issued changes a Project's visibility or workflows

### Requirement: The quality callee runs the caller's commands
The reusable workflow `quality.yml` SHALL take an optional `setup` and a required `test`
command from its caller. Its one job `quality` SHALL first verify that the PR links its issue,
then run `setup` when one is given and then `test` on the PR's checkout. A failing command
SHALL fail the job.

#### Scenario: Consumer test fails
- **WHEN** a caller's `test` command exits non-zero on a PR that links its issue
- **THEN** the `quality` job fails at that step

### Requirement: Callers reach the quality callee
A caller job of `quality.yml` SHALL be named `agent-process`, so the check reports as
`agent-process / quality`. A consumer caller SHALL call it at an immutable release tag
`@v<version>`. The publisher caller SHALL call it by a same-repository `./` path, which
takes caller and callee from the same commit.

#### Scenario: Consumer render
- **WHEN** the installer renders the managed caller for release `<version>`
- **THEN** its one job `agent-process` calls `ekolvah/agent-process-distribution/.github/workflows/quality.yml@v<version>` with `setup` and `test`

#### Scenario: Publisher PR
- **WHEN** a PR of this repository runs its workflows
- **THEN** `agent-process / quality` runs `python .agent-process/scripts/ci_check.py` from the callee at the PR's own commit
