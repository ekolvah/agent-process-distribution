## ADDED Requirements

### Requirement: Init asks for no quality command
`init` SHALL take no test or setup command. The quality commands of a repository SHALL live in
its own declaration `.github/agent-process-quality.json`, a JSON object with a non-blank string
`test` and optional string `setup` and `checks`, each on one line, which `init` never writes. While that file is
absent or declares no valid `test`, the plan of a dry-run and of a confirmed run SHALL print a
`manual quality-command` row saying CI runs no tests until the declaration exists. An existing
managed caller that passes a `test` input while the declaration declares no `test` SHALL be
reported as `conflict` naming that input, and the run SHALL exit non-zero before any write.

#### Scenario: Install without tests
- **WHEN** a dry-run or confirmed run meets a repository without `.github/agent-process-quality.json`
- **THEN** its output carries one `manual quality-command` row, and a confirmed run writes no declaration

#### Scenario: Declared quality command
- **WHEN** a dry-run or confirmed run meets a valid declaration of a `test`
- **THEN** its output carries no `manual quality-command` row

#### Scenario: Upgrade over a passed test command
- **WHEN** a run meets a managed caller that passes a `test` input and no declaration of a `test`
- **THEN** it prints `conflict` naming the passed command and the declaration file, exits non-zero, and no consumer file has changed

## RENAMED Requirements

- FROM: `### Requirement: The quality callee runs the caller's commands`
- TO: `### Requirement: The quality callee runs the declared commands`

## MODIFIED Requirements

### Requirement: The quality callee runs the declared commands
The reusable workflow `quality.yml` SHALL take no input and SHALL read `setup`, `test` and
`checks` from `.github/agent-process-quality.json` of the PR's checkout. A job SHALL verify
that the PR links its issue. When `checks` is declared, its output SHALL be a JSON array of
check names, and each name SHALL run `setup` when one is declared and then `test --only <name>`
on the PR's checkout, in a job of its own named after the check. A failing check job SHALL NOT
cancel another. Without `checks`, one job SHALL run `setup` and then `test`. When the file is
absent, the run SHALL execute no command of the PR and SHALL show a warning annotation saying
that no quality command is declared and the run tests nothing. A declaration that is not valid
JSON, is not an object, holds a `test` that is missing, blank or not a string, a `setup` or
`checks` that is not a string, or a value with a line break, SHALL fail the run with an error
naming the fault. The job
`quality` SHALL succeed only when the link job, the listing job, and every check job succeeded,
and SHALL fail otherwise, including when one of them was skipped or cancelled.

#### Scenario: Consumer test fails
- **WHEN** the declared `test` exits non-zero on a PR that links its issue
- **THEN** the `quality` job fails

#### Scenario: One check fails
- **WHEN** the declaration gives `checks`, and on a PR that links its issue one listed check exits non-zero
- **THEN** that check's job fails, every other listed check's job runs to its own conclusion, and the `quality` job fails

#### Scenario: Listing fails
- **WHEN** the declared `checks` command exits non-zero or prints anything but a non-empty JSON array of check names
- **THEN** the `quality` job fails

#### Scenario: No declaration
- **WHEN** a PR that links its issue has no `.github/agent-process-quality.json`
- **THEN** the run shows a warning annotation that no quality command is declared, runs no command of the PR, and the `quality` job succeeds

#### Scenario: Malformed declaration
- **WHEN** the declaration is not a JSON object with a non-blank string `test`, its `setup` or `checks` is not a string, or a value holds a line break
- **THEN** the run fails with an error naming the declaration file and the fault

### Requirement: Callers reach the quality callee
A caller job of `quality.yml` SHALL be named `agent-process`, so the check reports as
`agent-process / quality`, and SHALL pass no input. A consumer caller SHALL call it at an
immutable release tag `@v<version>`. The publisher caller SHALL call it by a same-repository
`./` path, which takes caller and callee from the same commit.

#### Scenario: Consumer render
- **WHEN** the installer renders the managed caller for release `<version>`
- **THEN** its one job `agent-process` calls `ekolvah/agent-process-distribution/.github/workflows/quality.yml@v<version>` with no input

#### Scenario: Publisher PR
- **WHEN** a PR of this repository runs its workflows
- **THEN** `agent-process / quality` runs `python .agent-process/scripts/ci_check.py` from the callee at the PR's own commit
