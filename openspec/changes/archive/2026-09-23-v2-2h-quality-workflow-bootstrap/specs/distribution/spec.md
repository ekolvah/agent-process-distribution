## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
A required quality context SHALL execute the process driver from the trusted default
branch against the PR worktree, so a PR cannot change what checks it. A context that runs
the PR's own driver SHALL NOT become required until its change names what catches a PR
that weakens that driver.

#### Scenario: Quality check on a PR
- **WHEN** a required quality context runs for a PR
- **THEN** the driver comes from the default branch and the PR's files are only its input
