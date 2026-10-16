## MODIFIED Requirements

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
worktree's status through the repository's `info/exclude`, adding its line only when absent.
It SHALL also prune `origin`'s remote-tracking refs whose
remote branch is gone, and for every local branch whose PR is merged, whose tip is that PR's
head commit, and which is checked out in no worktree or in a clean one under the main
worktree's `.claude/worktrees/` not containing the cwd, SHALL remove that worktree and delete
the branch, printing each removal and deletion. It SHALL keep and name on stderr a merged branch whose tip differs
from that head, whose worktree is dirty, or that it cannot remove or delete, and leave every
other branch and worktree untouched. A cleanup failure SHALL NOT fail the start.

#### Scenario: Main checkout stays clean
- **WHEN** `start_change` runs in a main checkout clean but for the untracked `openspec/changes/<change>/`, whose `info/exclude` lacks the `/.claude/worktrees/` line or already holds it
- **THEN** after the run `git status --porcelain` of the main checkout is empty, and `info/exclude` holds that line exactly once

#### Scenario: Merged change's worktree
- **WHEN** `start_change` runs while `.claude/worktrees/` holds a clean worktree whose branch is at its merged PR's head, a dirty one whose branch is at its merged PR's head, and one whose branch has an open PR or none
- **THEN** the first is removed and printed and its branch deleted, the second is kept and named on stderr, the third is untouched, and the start goes on to create its own branch

#### Scenario: Merged change's branch
- **WHEN** `start_change` runs while the repository holds, in no worktree, a branch at its merged PR's head whose `origin` branch is gone, a merged branch with a commit after its PR head, and a branch without a PR
- **THEN** the first branch and its `origin/<branch>` ref are deleted and the deletion printed, the second is kept and named on stderr, the third still exists, and `origin/main` remains

#### Scenario: Cleanup fails
- **WHEN** removing a merged clean worktree, deleting a merged branch at its PR head, or pruning the remote-tracking refs fails
- **THEN** stderr carries a `kept:` line naming the worktree, branch or remote and the failure, and `start_change` still creates its branch and exits 0

#### Scenario: Started from inside the previous change's worktree
- **WHEN** `start_change` runs with its cwd in `.claude/worktrees/<previous>` whose PR is merged
- **THEN** the new worktree is `.claude/worktrees/<change>` of the main worktree, not nested in the previous one, and the previous worktree and its branch survive the run

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
