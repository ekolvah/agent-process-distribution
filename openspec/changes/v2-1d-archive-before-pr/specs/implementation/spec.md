## ADDED Requirements

### Requirement: `archive_change` archives the change before its PR
One script, `archive_change <change>`, SHALL archive a change on its branch before the PR
opens: it SHALL refuse to run on a worktree that is not clean or while an archive lock
already exists; otherwise it SHALL mark its own task done, run `openspec archive <change> -y`,
remove the lock a successful archive leaves behind, commit and push, leaving a clean
worktree. It SHALL NOT request a review or wait for the PR: those are the delivery tasks that
follow it, ticked in `openspec/changes/archive/<date>-<change>/tasks.md`.

#### Scenario: Archive commit
- **WHEN** `archive_change` runs on a clean worktree
- **THEN** the archive commit is pushed before any PR exists, and the run continues with the PR tasks

#### Scenario: Stale archive lock
- **WHEN** an archive lock exists before `archive_change` runs
- **THEN** it reports the lock and exits without archiving or committing

## MODIFIED Requirements

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with the delivery tasks
(the priority asked before the tracking issue is created, `gh issue develop -c`,
`set_status "In Progress"`, the provenance line) and end with `ci_check`,
`archive_change <change>`, the PR and the `wait_for_pr` loop. After the tracking issue
exists no delivery task SHALL prompt the person. The review loop after the PR SHALL be
bounded: after three rounds of applying unresolved threads the run leaves the rest to the
person with a reply and ends. A re-run of the apply on an open PR SHALL continue from the
first unchecked task of the archived `tasks.md`. The PR body SHALL name the tracking issue
as a plain reference, not with a `Closes` keyword: the branch from `gh issue develop -c`
closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `agent-process` schema
- **THEN** its `tasks.md` begins with the priority and tracking-issue tasks, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule

## REMOVED Requirements

### Requirement: `finish_change` archives the change inside its PR
**Reason**: the archive moved in front of the PR (`archive_change`); a post-archive push
cost one review round on the head-bound `agent-review` check for a commit that changes no code.
**Migration**: `finish_change.py <change>` → `archive_change.py <change>` before `gh pr create`.
