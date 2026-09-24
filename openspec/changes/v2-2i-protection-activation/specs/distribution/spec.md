## MODIFIED Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
Every head of this repository SHALL be gated by a required context that the PR cannot
change: `quality / quality`, which runs the process driver from the trusted default branch
against the PR worktree, or `agent-review / agent-review`, which reviews that head. A
required context that runs the PR's own driver, `agent-process / quality`, SHALL be required
only beside one of them.

#### Scenario: Quality check on a PR
- **WHEN** `quality / quality` runs for a PR
- **THEN** the driver comes from the default branch and the PR's files are only its input

#### Scenario: PR weakens its own driver
- **WHEN** a PR of this repository changes the driver that `agent-process / quality` runs
- **THEN** the contexts the repository declares required for that head still include `quality / quality` or `agent-review / agent-review`

## ADDED Requirements

### Requirement: Protection activation observes quality first
`activate_protection` SHALL exit non-zero before any GitHub write unless two things hold.
The default branch SHALL carry `.github/workflows/agent-process.yml`. The current head of
the given PR against the default branch SHALL have a check run `agent-process / quality`
that concluded `success` from the GitHub Actions app. The required check SHALL bind the
integration ID of that app.

#### Scenario: Caller absent
- **WHEN** the default branch has no `.github/workflows/agent-process.yml`
- **THEN** the run names the missing caller, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Context not observed
- **WHEN** the PR's base is not the default branch, or its current head has no `agent-process / quality` check run, or that run did not succeed, or another app reported it
- **THEN** the run names what it observed on that head, exits non-zero, and every GitHub command it issued is a read

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
the strict policy, and the exact context with its integration ID.

#### Scenario: Read-back mismatch
- **WHEN** the ruleset read after a write lacks a barrier rule, has a bypass actor, or requires another context or integration
- **THEN** the run exits non-zero and names that field
