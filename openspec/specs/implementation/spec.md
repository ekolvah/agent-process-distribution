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
On an issue branch a Stop hook SHALL block the end of a turn while `ci_check` is not
recorded for the current head or the review gate has no terminal verdict for it, naming the
next command each time; on any other branch it SHALL never block. The block is bounded: after
`MAX_CONSECUTIVE_BLOCKS` consecutive turn-ends on an unchanged delivery state the hook lets
the turn end with an escalation marker instead of trapping the session.

#### Scenario: Missing CI record
- **WHEN** the turn ends on an issue branch without a `ci_check` record for the head
- **THEN** the hook blocks and names `ci_check`

#### Scenario: Terminal verdict
- **WHEN** the review gate is terminal for the current head
- **THEN** the turn ends

#### Scenario: Budget exhausted
- **WHEN** the delivery state has not changed across `MAX_CONSECUTIVE_BLOCKS` blocked turn-ends
- **THEN** the next turn-end is released with an escalation marker

### Requirement: A broken hook is visible
A hook that cannot do its job (linter missing, git state unreadable) SHALL surface a marker
or fail closed, never pass silently.

#### Scenario: Linter cannot run
- **WHEN** `ruff` fails to execute
- **THEN** the agent sees a setup marker instead of a clean result

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` before writing code; this is a `config.yaml` rule on `tasks`.
Documentation-only, rename and one-line non-behavioural changes are exempt (`principles.md`
§I). The project's test-runner command SHALL be declared in `AGENTS.md` together with the path
of the JUnit XML report it writes; `check_red` reads that report and requires nothing else
of the runner.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit contains a test that `check_red` reports as failing

### Requirement: GitHub links branch, PR and issue
The delivery tasks SHALL create the tracking issue when absent and the linked branch with
`gh issue develop -c N`; the PR links to the issue automatically and the merge closes it.

#### Scenario: Merge
- **WHEN** the PR from the linked branch merges
- **THEN** the issue closes without a body-text convention

### Requirement: `finish_change` archives the change inside its PR
One script, `finish_change <change>`, SHALL close a change on its PR: it SHALL refuse to run
on a worktree that is not clean or while an archive lock already exists; otherwise it SHALL
mark its own task done, run `openspec archive <change> -y`, remove the lock a successful
archive leaves behind, commit, push, re-request the Codex review and wait for that head with
`wait_for_pr`, leaving a clean worktree and nothing for the apply loop to edit.

#### Scenario: Archive commit
- **WHEN** `finish_change` pushes the archive commit
- **THEN** it waits for that commit's checks and reviews before the run ends, and the worktree is clean

#### Scenario: Stale archive lock
- **WHEN** an archive lock exists before `finish_change` runs
- **THEN** it reports the lock and exits without archiving or committing

### Requirement: The implementing run ends only after checks and reviews
The implementing run SHALL end only after the PR's checks and reviews are in on its head.
One blocking script, `wait_for_pr`, SHALL wait for checks and review threads and print the
unresolved ones; the run SHALL apply them and wait again until nothing is unresolved, or
reply on a thread it leaves to the person and end. A check that has not concluded — including
one that itself waits for a requested review — SHALL count as a pending review; a failed
check SHALL count as unresolved; threads SHALL be read only after every check on the head
has concluded. The end state SHALL never be ambiguous: nothing unresolved, unresolved items
printed, or a timeout reported as such.

#### Scenario: Pending review
- **WHEN** the PR is open and a review is pending
- **THEN** the run is blocked in `wait_for_pr` and cannot report completion
