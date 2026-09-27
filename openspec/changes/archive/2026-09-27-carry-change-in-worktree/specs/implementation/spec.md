## ADDED Requirements

### Requirement: A change is carried in its own worktree
`start_change <change>` SHALL carry the change in a worktree of its own at
`.claude/worktrees/<change>` of the repository's main worktree, wherever it runs, on the linked branch tracking `origin/<change>`, and SHALL move
the untracked `openspec/changes/<change>/` of the checkout it runs in into that worktree; it
SHALL NOT change the branch, the index or any other file of the checkout it runs in. Group 0
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

#### Scenario: Worktree step fails after the branch exists
- **WHEN** `gh issue develop` created the remote branch and a later worktree step fails
- **THEN** `start_change` exits 1 naming the steps left, starting with the one that failed, in order, before `set_status "In Progress"` and the provenance comment, and names no `git switch`

#### Scenario: Worktree listing fails
- **WHEN** `git worktree list --porcelain` fails after the gate
- **THEN** `start_change` exits 1 naming the error before any branch exists

## MODIFIED Requirements

### Requirement: GitHub links branch, PR and issue
The delivery tasks SHALL create the linked branch with `gh issue develop N --name <change>`,
without checkout, on the tracking issue the propose run left in `Planned`; the PR links to the
issue automatically and the merge closes it.

#### Scenario: Merge
- **WHEN** the PR from the linked branch merges
- **THEN** the issue closes without a body-text convention

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
