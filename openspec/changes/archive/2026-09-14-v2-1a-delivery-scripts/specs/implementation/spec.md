## Purpose
How the process gets correct implementations out of agents, how rework after CI is kept
low, and how an agent turn ends.

## ADDED Requirements

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
