# implementation Specification

## Purpose
What an implementing agent runs, what feedback it gets while working, and what stops it
from ending a turn with unfinished delivery.

## Requirements

### Requirement: ci_check is the one command every gate runs
One command, `ci_check`, SHALL be what the pre-push git hook and the CI workflow run; there
is no second list of checks.

#### Scenario: Push
- **WHEN** a branch is pushed
- **THEN** the pre-push hook runs `ci_check` after the protection probe, and CI runs the same command

### Requirement: Shift-left feedback in Claude
A PostToolUse hook SHALL run `ruff` on a Python file right after it is edited and surface
findings to the agent; a PreToolUse hook SHALL deny shell navigation of the repository
(`cat`, `grep`, `find`, `sed -n`, whole-file reads over the budget) and name the cheaper
route.

#### Scenario: Lint error
- **WHEN** an edit introduces a lint error
- **THEN** the agent sees the finding before its next tool call

#### Scenario: Shell navigation
- **WHEN** a shell command contains a denied navigation stage anywhere in a pipeline
- **THEN** the command is denied and the response names the tool to use instead

### Requirement: Stop hook names the next command
On an issue branch a Stop hook SHALL block the end of a turn until `ci_check` is recorded
for the current head and the review gate has a terminal verdict for it, naming the next
command each time; on any other branch it SHALL never block.

#### Scenario: Missing CI record
- **WHEN** the turn ends on an issue branch without a `ci_check` record for the head
- **THEN** the hook blocks and names `ci_check`

#### Scenario: Terminal verdict
- **WHEN** the review gate is terminal for the current head
- **THEN** the turn ends

### Requirement: A broken hook is visible
A hook that cannot do its job (linter missing, git state unreadable) SHALL surface a marker
or fail closed, never pass silently.

#### Scenario: Linter cannot run
- **WHEN** `ruff` fails to execute
- **THEN** the agent sees a setup marker instead of a clean result

### Requirement: Principles are one file within the read budget
The principles SHALL be one file, `principles.md`, small enough to be read whole.

#### Scenario: Read budget
- **WHEN** the read-budget documents are measured
- **THEN** `principles.md` fits as a whole-file read
