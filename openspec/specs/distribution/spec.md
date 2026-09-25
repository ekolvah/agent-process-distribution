# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

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

### Requirement: Protection activation observes quality first
`activate_protection` SHALL exit non-zero before any GitHub write unless two things hold.
The default branch SHALL carry `.github/workflows/agent-process.yml`. The current head of
the given PR against the default branch SHALL have a check run `agent-process / quality`
that concluded `success` from the GitHub Actions app. When the default branch also carries
`.github/workflows/agent-review.yml`, the same head SHALL have a check run
`agent-review / agent-review` that concluded `success` from that app, and the run SHALL
require both contexts. Each required check SHALL bind the integration ID of the app that
reported it.

#### Scenario: Caller absent
- **WHEN** the default branch has no `.github/workflows/agent-process.yml`
- **THEN** the run names the missing caller, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Context not observed
- **WHEN** the PR's base is not the default branch, or its current head has no `agent-process / quality` check run, or that run did not succeed, or another app reported it
- **THEN** the run names what it observed on that head, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Review caller present
- **WHEN** the default branch carries `.github/workflows/agent-review.yml` and the PR head has successful `agent-process / quality` and `agent-review / agent-review` runs from GitHub Actions
- **THEN** the planned ruleset requires both contexts, each with that app's integration ID

#### Scenario: Review context not observed
- **WHEN** the default branch carries `.github/workflows/agent-review.yml` and the PR head has no successful `agent-review / agent-review` run from GitHub Actions
- **THEN** the run names what it observed for that context, exits non-zero, and every GitHub command it issued is a read

### Requirement: Activation previews every remote write
A run SHALL print one line per ruleset transition, marked `planned`, `unchanged`, or
`conflict`. A rollback command SHALL follow each `planned` line. The run SHALL print the
required contexts of classic branch protection as read. A dry-run SHALL issue only GitHub
reads.

#### Scenario: Dry-run
- **WHEN** a dry-run completes on a repository whose ruleset differs from the process ruleset
- **THEN** it prints the `planned` update and its rollback command, prints the classic protection read, and every GitHub command it issued is a read

### Requirement: Activation converges one ruleset
A confirmed run SHALL leave exactly one repository ruleset named `agent-process default
branch`. It SHALL create that ruleset when none exists. It SHALL update the ruleset in place
when an owned field differs, and write nothing when all owned fields are equal. Several
rulesets with that name, or one whose source is not the repository, SHALL be a `conflict`,
and the run SHALL exit non-zero before its first write. The run SHALL NOT write classic
branch protection.

#### Scenario: No ruleset yet
- **WHEN** a confirmed run meets a repository with no ruleset of that name
- **THEN** it creates one ruleset and writes nothing else

#### Scenario: Live ruleset differs
- **WHEN** the one ruleset of that name requires another context
- **THEN** a confirmed run updates that ruleset under the same ID and creates none

#### Scenario: Rerun
- **WHEN** a confirmed run is repeated after it succeeded
- **THEN** it reports the ruleset `unchanged` and issues no write

#### Scenario: Ambiguous rulesets
- **WHEN** two rulesets carry the process name, or the one that does is not repository-owned
- **THEN** a dry-run or confirmed run prints `conflict` naming them, exits non-zero, and has issued no write

### Requirement: Activation reads back what it wrote
After a write, the run SHALL read the ruleset back and SHALL exit non-zero on the first
field that differs, and name it. The checked fields are the default-branch ref, active
enforcement, the pull request, deletion, and non-fast-forward rules, the empty bypass list,
the strict policy, and the exact set of required contexts, each with its integration ID, in
any order.

#### Scenario: Read-back mismatch
- **WHEN** the ruleset read after a write lacks a barrier rule, has a bypass actor, requires another context or integration, or lacks or adds a context
- **THEN** the run exits non-zero and names that field

#### Scenario: Read-back reorders contexts
- **WHEN** the ruleset read after a write returns the written contexts in another order
- **THEN** the read-back passes, and a later dry-run prints `unchanged`

### Requirement: A context the PR cannot change gates every head
Every head of this repository SHALL be gated by a required context that the PR cannot
change: `agent-review / agent-review`, which reviews that head. A required context that runs
the PR's own driver, `agent-process / quality`, SHALL be required only beside it. Each PR
SHALL run the quality driver once.

#### Scenario: PR weakens its own driver
- **WHEN** a PR of this repository changes the driver that `agent-process / quality` runs
- **THEN** the contexts the repository declares required for that head still include `agent-review / agent-review`

#### Scenario: Quality runs once per PR
- **WHEN** a PR of this repository opens or receives a push
- **THEN** `agent-process / quality` is the only check run that executes the quality driver on its head

### Requirement: Package paths resolve in a consumer
A file of the package — the skill directory, `agents/`, and `commands/` — SHALL NOT name a
path under the publisher's `.agent-process/` root, and no relative Markdown link of a skill
file SHALL leave the skill directory. The principles the architect review applies SHALL be a
file of the skill directory. A plugin agent SHALL name each package file by its path in the
skill directory, from the repository root, and SHALL name `${CLAUDE_PLUGIN_ROOT}` as the root
where the repository has no skill directory.

#### Scenario: Publisher-only path in the package
- **WHEN** a package file names a `.agent-process/` path, a skill file links a relative target outside the skill directory, or a plugin agent names a path in the skill directory that is not a package file or names no `${CLAUDE_PLUGIN_ROOT}` fallback
- **THEN** the publisher tests fail and name that file and path
