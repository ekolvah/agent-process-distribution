# implementation Specification

## Purpose
What an implementing agent runs and what feedback it gets while working.

## Requirements

### Requirement: ci_check is the one command every gate runs
One command, `ci_check`, SHALL be what the pre-push git hook and the CI workflow run; there
is no second list of checks. `ci_check` SHALL run the `pre-commit`-stage hooks of
`.pre-commit-config.yaml` over all files, so the checks run after an edit are part of the gate.

#### Scenario: Push
- **WHEN** a branch is pushed
- **THEN** the pre-push hook runs `ci_check` as its only check, and CI runs the same command

#### Scenario: Edit-time check in the gate
- **WHEN** a file fails a `pre-commit`-stage hook of `.pre-commit-config.yaml`
- **THEN** `ci_check` exits non-zero with that hook's output, and runs no `pre-push`-stage hook

### Requirement: Shift-left feedback in Claude
A PostToolUse hook SHALL run the project's `pre-commit`-stage hooks of `.pre-commit-config.yaml`
on a file right after it is edited and surface their findings to the agent; a PreToolUse hook
SHALL deny shell navigation of the repository (`cat`, `grep`, `find`, `sed -n`, whole-file
reads over the budget) and name the cheaper route.

#### Scenario: Lint error
- **WHEN** an edit introduces an error that a `pre-commit`-stage hook of the project reports
- **THEN** the agent sees the finding before its next tool call

#### Scenario: Shell navigation
- **WHEN** a shell command contains a denied navigation stage anywhere in a pipeline
- **THEN** the command is denied and the response names the tool to use instead

### Requirement: A broken hook is visible
A hook that cannot do its job (`pre-commit` missing or its config unreadable, git state
unreadable) SHALL surface a marker or fail closed, never pass silently.

#### Scenario: Linter cannot run
- **WHEN** `pre-commit` is not on `PATH`, or cannot load the project's `.pre-commit-config.yaml`
- **THEN** the agent sees a marker naming the cause instead of a clean result

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` before writing code; this is a `config.yaml` rule on `tasks`.
Documentation-only, rename and one-line non-behavioural changes are exempt (`principles.md`
§I). The RED commit SHALL be the first commit after the plan commit of `start_change` and
SHALL carry the Group 1 ticks; the commit that ends every later group SHALL carry that
group's ticks. `check_red` SHALL run `python -m pytest` of the `python` on `PATH`, not of the
interpreter that runs the script, under its own
configuration — fail-fast cancelled, the cache-driven selection and stepping disabled, a
JUnit XML report path of its own choosing — with the node ids appended, and SHALL take the
verdict per test from that report, whole; it SHALL require no runner declaration and no
report path of the project. While no `python` is on `PATH`, `check_red` SHALL exit 2 naming
`python` and run nothing. `check_red` SHALL write nothing of its own into the working tree — no bytecode,
no cache, no report. Before running
anything, `check_red` SHALL exit 2 while `.github/agent-process-quality.json` of the current
directory declares no valid `test`, naming that file and the fault, so the change that
brings a repository's first tests declares its quality command.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit after the plan commit contains a test that `check_red` reports as failing, and the Group 1 ticks

#### Scenario: Runner given
- **WHEN** `check_red` is called with node ids
- **THEN** the runner is a given — `python -m pytest` of the `python` on `PATH`, whatever interpreter runs the script, no runner argument — and it runs with the report path and the node ids appended and judges RED from the report the run wrote, without any declared report path

#### Scenario: No python on PATH
- **WHEN** `check_red` is called with node ids and no `python` is on `PATH`
- **THEN** it exits 2 naming `python`, and runs no test

#### Scenario: Configuration that cuts the run
- **WHEN** the project's pytest configuration carries a flag that stops the run early or replays a previous run (`-x`, `--maxfail`, `--stepwise`, `--lf`, `--ff`)
- **THEN** `check_red` either runs every node id regardless or exits 2 with the runner's output, never RED from a partial report

#### Scenario: No quality command declared
- **WHEN** `check_red` runs where `.github/agent-process-quality.json` is absent or declares no valid `test`
- **THEN** it exits 2 naming the declaration file and the fault, and runs no test

#### Scenario: Run leaves the tree clean
- **WHEN** `check_red` runs in a git repository that has no ignore rule for bytecode caches
- **THEN** `git status --porcelain` prints the same after the run as before it

### Requirement: GitHub links branch, PR and issue
The delivery tasks SHALL create the linked branch with `gh issue develop N --name <change>`,
without checkout, on the tracking issue the propose run left in `Planned`; the PR links to the
issue automatically and the merge closes it.

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
<change>` — the gate (the review file validated, its verdict read, and the tracking issue as a Project item in
`Planned`), `gh issue develop` on that issue, the change's worktree, `set_status "In Progress"` and the
provenance line in one command whose conditions are exit codes — and end with `ci_check`,
`archive_change <change>`, the PR and the `wait_for_pr` loop. No delivery task SHALL
prompt the person or create the issue: the area was chosen by the propose run, which
SHALL write the issue number into Group 0 of `tasks.md` (the placeholder `<N>` replaced).
`start_change` SHALL exit 2 without creating a branch when `architect-review.json` is not
valid against `skills/agent-process/architect-review.schema.json` or its verdict is not
`approve`, and SHALL print `propose run not finished` and exit 2 when `tasks.md` still
reads `<N>` or the issue is not in `Planned`. The review loop after the PR SHALL be
bounded: after three rounds of applying unresolved threads the run leaves the rest to the
person with a reply and ends. The loop SHALL name how a `P0`/`P1` thread the push addressed
is resolved — `resolve_review_thread --thread --reply-file` on that thread from the
implementer's own session — and SHALL resolve no other thread: a `P2`/`P3` finding is
answered, and its disposition is the person's. The step after `wait_for_pr` is that one
command, and its order is the script's, not the rule's: it SHALL refuse while the head's
`agent-review` run is running (the review of the head is in when the run concluded), resolve the thread, re-run that
run (a resolve has no event of its own, and the required context is the head's
`pull_request` run) and post the reply last. A review fix that changes a spec SHALL go
through a change of its own on the PR branch — a delta under
`openspec/changes/<change>/specs/`, validated and archived by `archive_change` before the
push — never through a direct edit of `openspec/specs/`: the archive is what carries a
spec, on the first PR and on every fix. A review fix that changes a design decision SHALL
amend the archived `design.md` beside that decision and the scenario → test map of the
archived `tasks.md` in the same push. A review finding on what a script does SHALL be
closed by its class: the fix names the invariant the finding violates, enumerates the
other inputs that violate it from the tool's own documentation, states what each added
flag or switch takes away, and the RED test covers the class, not the reviewer's example.
The tasks after the archive SHALL leave no tick in
the repository — the PR is their record — and a run interrupted after the archive SHALL
resume from `gh pr view <change>`, not from the apply. The PR body SHALL name the tracking
issue as a plain reference, not with a `Closes` keyword: the linked branch from `gh issue
develop` closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` begins with `start_change <change>` on an existing tracking issue, asks nothing, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule

#### Scenario: Propose run stopped before its tail
- **WHEN** `start_change` runs on a change whose `tasks.md` still reads `<N>` or whose tracking issue is not in `Planned`
- **THEN** it prints `propose run not finished` and exits 2 before any branch exists, asking nothing

#### Scenario: Verdict is rework
- **WHEN** `start_change` runs while `architect-review.json` is not valid against the review schema or its `verdict` is not `approve`
- **THEN** it exits 2 before any branch exists and names the rework or the validation error

#### Scenario: Blocking thread addressed
- **WHEN** a push of the review loop addresses a `P0`/`P1` thread
- **THEN** the Deliver group of `tasks.md` names `resolve_review_thread --thread --reply-file` for that thread and names no resolve for a `P2`/`P3` thread; the script refuses while the head's `agent-review` run is running, and on a concluded run resolves the thread, re-runs that run and posts the reply, in that order

#### Scenario: Review fix changes a spec
- **WHEN** a fix in the review loop changes what a spec requires
- **THEN** the Deliver group names a change of its own for it — delta, validation, `archive_change` — and `openspec/specs/` is edited by the archive alone

#### Scenario: Design decision changed at review
- **WHEN** a fix in the review loop changes a design decision of the archived change
- **THEN** the Deliver group names the amendment of the archived `design.md` beside that decision and of the scenario → test map of the archived `tasks.md`, in the same push as the fix

#### Scenario: Finding closed by its class
- **WHEN** a fix in the review loop closes a review finding on what a script does
- **THEN** the Deliver group names the invariant, the enumeration of the other violating inputs from the tool's own documentation, what each added flag takes away, and a RED test of the class, not of the reviewer's example

### Requirement: `archive_change` archives the change before its PR
One script, `archive_change <change>`, SHALL archive a change on its branch before the PR
opens: it SHALL refuse to run while the worktree holds any change other than a modification
of `openspec/changes/<change>/tasks.md` or while an archive lock already exists; otherwise it
SHALL mark its own task done, run `openspec archive <change> -y`, remove the lock a successful
archive leaves behind, commit — the ticks left in `tasks.md` included — and push, leaving a
clean worktree. It SHALL NOT request a review or wait for the PR: those are the delivery tasks
that follow it, recorded by the PR itself.

#### Scenario: Archive commit
- **WHEN** `archive_change` runs on a clean worktree
- **THEN** the archive commit is pushed before any PR exists, and the run continues with the PR tasks

#### Scenario: Ticks left for the archive
- **WHEN** `archive_change` runs while the only uncommitted change is ticks in `openspec/changes/<change>/tasks.md`, again while another file is also changed, and again while that `tasks.md` is deleted
- **THEN** the first run's archive commit carries those ticks and leaves the worktree clean; the second and third exit 2 naming the other file or the deleted `tasks.md`, before archiving or committing

#### Scenario: Stale archive lock
- **WHEN** an archive lock exists before `archive_change` runs
- **THEN** it reports the lock and exits without archiving or committing

### Requirement: ci_check limits code complexity
`ci_check` SHALL fail when a function exceeds the configured complexity limits or a Python
module exceeds the configured size limit. A complexity suppression that no longer suppresses
anything SHALL fail.

#### Scenario: Function over the complexity limit
- **WHEN** a Python function in a linted scope exceeds the complexity limit without a suppression
- **THEN** `ci_check` exits non-zero and names the function and the rule

#### Scenario: Module over the size limit
- **WHEN** a Python module in a checked scope exceeds the size limit
- **THEN** `ci_check` exits non-zero and names the module

#### Scenario: Stale baseline entry
- **WHEN** a complexity suppression remains on a function that no longer exceeds the limit
- **THEN** `ci_check` exits non-zero and names the unused suppression

### Requirement: The delivered change is explained for solution review
When `wait_for_pr` settles the head or the review loop escalates, the implementing run SHALL
end with a plain-words explanation of the delivered change, published as a page linked in the
final message, or written in that message when the carrier cannot publish a page.

#### Scenario: Run ends
- **WHEN** the implementing run stops after its PR
- **THEN** its final message links or carries the plain-words explanation of the delivered change

### Requirement: ci_check forbids test-to-test imports
`ci_check` SHALL fail when a test module imports another test module. A test module MAY import
a non-test helper module.

#### Scenario: Test module imports a test module
- **WHEN** a test module imports another test module, while another imports only a helper module
- **THEN** `ci_check` exits non-zero and names the importing and the imported test module, and reports nothing for the helper import

### Requirement: The PR title carries a Conventional Commit type
The Deliver group of every `tasks.md` SHALL open the PR with the title `<type>: <change>`,
where `<type>` is the Conventional Commit type the planner chose for the change: `feat` or
`fix` when behaviour changes, otherwise a type that cuts no release (`docs`, `test`,
`refactor`, `chore`). The squash commit of the PR on `main` SHALL carry that title. In this
repository a `pr-title` check SHALL run on every opened, edited, pushed, or reopened PR and
SHALL fail when the title is not a Conventional Commit of one of those types; a ruleset of its
own, beside the process ruleset, SHALL require that check for a merge into `main`.

#### Scenario: Behaviour change delivered
- **WHEN** a change that alters behaviour is merged
- **THEN** its commit on `main` is titled `feat: <change>` or `fix: <change>`, and the next release PR counts it

#### Scenario: Title without a type
- **WHEN** a PR into `main` is titled without an allowed Conventional Commit type
- **THEN** its `pr-title` check fails and the PR cannot be merged until an edited title passes the re-run check

### Requirement: ci_check lists its checks
`ci_check --list` SHALL print the names of its check registry as one JSON array, in run
order, and exit zero without running a check.

#### Scenario: List
- **WHEN** `ci_check --list` runs
- **THEN** stdout is a JSON array equal to the registry names in order, and no check command was started

### Requirement: ci_check scans secrets within the command-line limit
The `secrets` check of `ci_check` SHALL scan every target it selects, passing them in batches so
that no command line it starts exceeds the Windows limit of 32767 characters, and SHALL fail
when any batch reports a finding.

#### Scenario: Targets beyond one command line
- **WHEN** the targets' single command line would exceed 32767 characters and a secret sits in a file of the last batch
- **THEN** every started command line is at most the limit, the batches together pass every target once, and `ci_check` exits non-zero

### Requirement: A change is carried in its own worktree
`start_change <change>` SHALL carry the change in a worktree of its own at
`.claude/worktrees/<change>` of the repository's main worktree, wherever it runs, on the linked branch tracking `origin/<change>`, and SHALL move
the untracked `openspec/changes/<change>/` of the checkout it runs in into that worktree; it
SHALL NOT change the branch, the index or any other file of the checkout it runs in. There it
SHALL tick its own Group 0 task and commit `openspec/changes/<change>/` on the linked branch —
the plan commit, not pushed — leaving that worktree clean. Group 0
SHALL enter that worktree, and every later task of the apply SHALL run there. A failure once
the remote branch exists SHALL name the steps left, beginning with the worktree step that did
not run; a run interrupted before the archive SHALL resume by entering the same worktree.
Before creating the branch, `start_change` SHALL keep `.claude/worktrees/` out of the main
worktree's status through the repository's `info/exclude`, adding its line only when absent,
and SHALL remove every worktree under the main
worktree's `.claude/worktrees/`, other than the one containing its cwd, whose branch's PR is merged and whose tree is clean, print each removal,
keep and name on stderr a merged one it cannot remove or that is dirty, leave every other
worktree untouched, and not fail the start on a cleanup failure.

#### Scenario: Main checkout stays clean
- **WHEN** `start_change` runs in a main checkout clean but for the untracked `openspec/changes/<change>/`, whose `info/exclude` lacks the `/.claude/worktrees/` line or already holds it
- **THEN** after the run `git status --porcelain` of the main checkout is empty, and `info/exclude` holds that line exactly once

#### Scenario: Merged change's worktree
- **WHEN** `start_change` runs while `.claude/worktrees/` holds a clean worktree whose PR is merged, a dirty one whose PR is merged, and one whose branch has an open PR or none
- **THEN** the first is removed and printed, the second is kept and named on stderr, the third is untouched, and the start goes on to create its own branch

#### Scenario: Started from inside the previous change's worktree
- **WHEN** `start_change` runs with its cwd in `.claude/worktrees/<previous>` whose PR is merged
- **THEN** the new worktree is `.claude/worktrees/<change>` of the main worktree, not nested in the previous one, and the previous worktree survives the run

#### Scenario: Cleanup fails
- **WHEN** removing a merged clean worktree fails
- **THEN** stderr carries a `kept:` line naming the worktree and the failure, and `start_change` still creates its branch and exits 0

#### Scenario: Parallel changes
- **WHEN** `start_change` runs for change `b` in a checkout on `main` that also holds the untracked `openspec/changes/a/` of another change
- **THEN** the checkout is still on `main` and still holds `openspec/changes/a/`, and `openspec/changes/b/` is in `.claude/worktrees/b`, whose worktree is on branch `b` tracking `origin/b`

#### Scenario: Plan committed
- **WHEN** `start_change` has moved `openspec/changes/<change>/` into its worktree
- **THEN** the worktree's `git status --porcelain` is empty, its head commit carries `openspec/changes/<change>/` with the Group 0 task ticked, and `origin/<change>` does not carry that commit

#### Scenario: Worktree step fails after the branch exists
- **WHEN** `gh issue develop` created the remote branch and a later worktree step fails
- **THEN** `start_change` exits 1 naming the steps left, starting with the one that failed, in order, before `set_status "In Progress"` and the provenance comment, and names no `git switch`

#### Scenario: Worktree listing fails
- **WHEN** `git worktree list --porcelain`, or the read or write of `info/exclude`, fails after the gate
- **THEN** `start_change` exits 1 naming the error before any branch exists

### Requirement: A collection failure names the way to RED
When a `check_red` run does not complete, `check_red` SHALL still exit 2 without a verdict,
and its stderr SHALL name the way to a judgeable RED for a test module that failed at
collection because its import target does not exist yet: a stub of the target whose body
raises `NotImplementedError`, so the test fails in its body.

#### Scenario: Test of code that does not exist yet
- **WHEN** `check_red` runs node ids of a test module whose import target does not exist
- **THEN** it exits 2, and its stderr names the module that failed at collection and the `NotImplementedError` stub

### Requirement: ci_check type-checks
`ci_check` SHALL type-check its Python modules with mypy and SHALL fail on a type error. A test
module that imports a helper module by its package path SHALL NOT stop the check.

#### Scenario: Type error
- **WHEN** a module has a type error, while a test module imports a helper module by its package path
- **THEN** `ci_check` exits non-zero and names the module and the error, and reports no module found twice
