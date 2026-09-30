## MODIFIED Requirements

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` before writing code; this is a `config.yaml` rule on `tasks`.
Documentation-only, rename and one-line non-behavioural changes are exempt (`principles.md`
§I). The RED commit SHALL be the first commit after the plan commit of `start_change` and
SHALL carry the Group 1 ticks; the commit that ends every later group SHALL carry that
group's ticks. `check_red` SHALL run `python -m pytest` of its own interpreter under its own
configuration — fail-fast cancelled, the cache-driven selection and stepping disabled, a
JUnit XML report path of its own choosing — with the node ids appended, and SHALL take the
verdict per test from that report, whole; it SHALL require no runner declaration and no
report path of the project. `check_red` SHALL write nothing of its own into the working tree — no bytecode,
no cache, no report. Before running
anything, `check_red` SHALL exit 2 while `.github/agent-process-quality.json` of the current
directory declares no valid `test`, naming that file and the fault, so the change that
brings a repository's first tests declares its quality command.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit after the plan commit contains a test that `check_red` reports as failing, and the Group 1 ticks

#### Scenario: Runner given
- **WHEN** `check_red` is called with node ids
- **THEN** the runner is a given — `python -m pytest` of the interpreter that runs the script, no runner argument — and it runs with the report path and the node ids appended and judges RED from the report the run wrote, without any declared report path

#### Scenario: Configuration that cuts the run
- **WHEN** the project's pytest configuration carries a flag that stops the run early or replays a previous run (`-x`, `--maxfail`, `--stepwise`, `--lf`, `--ff`)
- **THEN** `check_red` either runs every node id regardless or exits 2 with the runner's output, never RED from a partial report

#### Scenario: No quality command declared
- **WHEN** `check_red` runs where `.github/agent-process-quality.json` is absent or declares no valid `test`
- **THEN** it exits 2 naming the declaration file and the fault, and runs no test

#### Scenario: Run leaves the tree clean
- **WHEN** `check_red` runs in a git repository that has no ignore rule for bytecode caches
- **THEN** `git status --porcelain` prints the same after the run as before it

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
Before creating the branch, `start_change` SHALL remove every worktree under the main
worktree's `.claude/worktrees/`, other than the one containing its cwd, whose branch's PR is merged and whose tree is clean, print each removal,
keep and name on stderr a merged one it cannot remove or that is dirty, leave every other
worktree untouched, and not fail the start on a cleanup failure.

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
- **WHEN** `git worktree list --porcelain` fails after the gate
- **THEN** `start_change` exits 1 naming the error before any branch exists
