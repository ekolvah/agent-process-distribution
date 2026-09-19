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
§I). `check_red` SHALL run `python -m pytest` of its own interpreter under its own
configuration — fail-fast cancelled, the cache-driven selection and stepping disabled, a
JUnit XML report path of its own choosing — with the node ids appended, and SHALL take the
verdict per test from that report, whole; it SHALL require no runner declaration and no
report path of the project.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit contains a test that `check_red` reports as failing

#### Scenario: Runner given
- **WHEN** `check_red` is called with node ids
- **THEN** the runner is a given — `python -m pytest` of the interpreter that runs the script, no runner argument — and it runs with the report path and the node ids appended and judges RED from the report the run wrote, without any declared report path

#### Scenario: Configuration that cuts the run
- **WHEN** the project's pytest configuration carries a flag that stops the run early or replays a previous run (`-x`, `--maxfail`, `--stepwise`, `--lf`, `--ff`)
- **THEN** `check_red` either runs every node id regardless or exits 2 with the runner's output, never RED from a partial report

### Requirement: GitHub links branch, PR and issue
The delivery tasks SHALL create the linked branch with `gh issue develop -c N` on the
tracking issue the propose run left in `Planned`; the PR links to the issue automatically
and the merge closes it.

#### Scenario: Merge
- **WHEN** the PR from the linked branch merges
- **THEN** the issue closes without a body-text convention

### Requirement: The implementing run ends only after checks and reviews
The implementing run SHALL end only after the PR's checks and reviews are in on its head.
One blocking script, `wait_for_pr`, SHALL read the head's checks as `gh pr checks` reports
them until the head reports at least one check and none is pending, then read the review
threads and print the unresolved ones; the run SHALL apply them and wait again until
nothing is unresolved, or reply on a thread it leaves to the person and end. A check that
has not concluded SHALL count as a pending review; the wait for a requested review SHALL be
the `agent-review` check's own bounded wait, not the script's; a failed or cancelled check
SHALL count as unresolved; threads SHALL be read only after every check on the head has
concluded. The end state SHALL never be ambiguous: nothing unresolved (exit 0), unresolved
items printed (exit 1), a `gh` failure reported with its message (exit 2), or a timeout
reported with what was still awaited (exit 3).

#### Scenario: Pending review
- **WHEN** the PR is open and a review is pending
- **THEN** the run is blocked in `wait_for_pr` and cannot report completion

#### Scenario: Empty rollup after a push
- **WHEN** `wait_for_pr` runs before any check has attached to the head
- **THEN** it reads again instead of reporting clean or failed, and reads threads only once every check of the head has concluded

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with `start_change
<change>` — the gate (the verdict read and the tracking issue as a Project item in
`Planned`), `gh issue develop -c` on that issue, `set_status "In Progress"` and the
provenance line in one command whose conditions are exit codes — and end with `ci_check`,
`archive_change <change>`, the PR and the `wait_for_pr` loop. No delivery task SHALL
prompt the person or create the issue: the priority was asked by the propose run, which
SHALL write the issue number into Group 0 of `tasks.md` (the placeholder `<N>` replaced).
`start_change` SHALL exit 2 without creating a branch when the verdict does not start with
`approve`, and SHALL print `propose run not finished` and exit 2 when `tasks.md` still
reads `<N>` or the issue is not in `Planned`. The review loop after the PR SHALL be
bounded: after three rounds of applying unresolved threads the run leaves the rest to the
person with a reply and ends. The loop SHALL name how a `P0`/`P1` thread the push addressed
is resolved — `resolve_review_thread --thread --reply-file` on that thread from the
implementer's own session — and SHALL resolve no other thread: a `P2`/`P3` finding is
answered, and its disposition is the person's. The step after `wait_for_pr` is that one
command, and its order is the script's, not the rule's: it SHALL refuse while the head's
`agent-review` run is running (the review of the head is in when the run concluded,
Codex's or the fallback's the run started when none came), resolve the thread, re-run that
run (a resolve has no event of its own, and the required context is the head's
`pull_request` run) and post the reply last. A review fix that changes a spec SHALL go
through a change of its own on the PR branch — a delta under
`openspec/changes/<change>/specs/`, validated and archived by `archive_change` before the
push — never through a direct edit of `openspec/specs/`: the archive is what carries a
spec, on the first PR and on every fix. The tasks after the archive SHALL leave no tick in
the repository — the PR is their record — and a run interrupted after the archive SHALL
resume from `gh pr view <change>`, not from the apply. The PR body SHALL name the tracking
issue as a plain reference, not with a `Closes` keyword: the branch from `gh issue develop
-c` closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` begins with `start_change <change>` on an existing tracking issue, asks nothing, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule

#### Scenario: Propose run stopped before its tail
- **WHEN** `start_change` runs on a change whose `tasks.md` still reads `<N>` or whose tracking issue is not in `Planned`
- **THEN** it prints `propose run not finished` and exits 2 before any branch exists, asking nothing

#### Scenario: Verdict is rework
- **WHEN** `start_change` runs while `architect-review.md` does not start its verdict with `approve`
- **THEN** it exits 2 before any branch exists and names the rework

#### Scenario: Blocking thread addressed
- **WHEN** a push of the review loop addresses a `P0`/`P1` thread
- **THEN** the Deliver group of `tasks.md` names `resolve_review_thread --thread --reply-file` for that thread and names no resolve for a `P2`/`P3` thread; the script refuses while the head's `agent-review` run is running, and on a concluded run resolves the thread, re-runs that run and posts the reply, in that order

#### Scenario: Review fix changes a spec
- **WHEN** a fix in the review loop changes what a spec requires
- **THEN** the Deliver group names a change of its own for it — delta, validation, `archive_change` — and `openspec/specs/` is edited by the archive alone

### Requirement: `archive_change` archives the change before its PR
One script, `archive_change <change>`, SHALL archive a change on its branch before the PR
opens: it SHALL refuse to run on a worktree that is not clean or while an archive lock
already exists; otherwise it SHALL mark its own task done, run `openspec archive <change> -y`,
remove the lock a successful archive leaves behind, commit and push, leaving a clean
worktree. It SHALL NOT request a review or wait for the PR: those are the delivery tasks that
follow it, recorded by the PR itself.

#### Scenario: Archive commit
- **WHEN** `archive_change` runs on a clean worktree
- **THEN** the archive commit is pushed before any PR exists, and the run continues with the PR tasks

#### Scenario: Stale archive lock
- **WHEN** an archive lock exists before `archive_change` runs
- **THEN** it reports the lock and exits without archiving or committing
