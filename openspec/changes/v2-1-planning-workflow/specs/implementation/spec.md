## Purpose
How the process gets correct implementations out of agents, how rework after CI is kept
low, and how an agent turn ends.

## ADDED Requirements

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` before writing code; this is a `config.yaml` rule on `tasks`.
Documentation-only, rename and one-line non-behavioural changes are exempt (`principles.md`
§I). The project's test-runner command SHALL be declared in `AGENTS.md`; the only
requirement on it is an exit code.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit contains a test that `check_red` reports as failing

### Requirement: GitHub links branch, PR and issue
The delivery tasks SHALL create the tracking issue when absent and the linked branch with
`gh issue develop -c N`; the PR links to the issue automatically and the merge closes it.

#### Scenario: Merge
- **WHEN** the PR from the linked branch merges
- **THEN** the issue closes without a body-text convention

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with the delivery tasks
(tracking issue with priority, `gh issue develop -c`, `set_status In progress`) and end with
`ci_check`, the PR, the `wait_for_pr` loop, `openspec archive <change> -y`, the push of the
archive commit and a final `wait_for_pr`. No delivery task SHALL prompt the person.

#### Scenario: Archive commit
- **WHEN** the run pushes the archive commit
- **THEN** it waits for that commit's checks and reviews before it ends

### Requirement: The implementing run ends only after checks and reviews
The implementing run SHALL end only after the PR's checks and reviews are in on its head.
One blocking script, `wait_for_pr`, SHALL wait for checks and review threads and print the
unresolved ones; the run SHALL apply them and wait again until nothing is unresolved, or
reply on a thread it leaves to the person and end.

#### Scenario: Pending review
- **WHEN** the PR is open and a review is pending
- **THEN** the run is blocked in `wait_for_pr` and cannot report completion
