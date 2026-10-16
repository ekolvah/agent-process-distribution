## Why

Local branches of merged changes accumulate: on 2026-10-16 the main checkout held 66 local
branches, 54 with upstream `gone`, plus stale `origin/<change>` refs of branches GitHub had
already deleted (`git fetch --prune --dry-run` listed 10). The merge lands after the agent's
run (auto-merge on the person's approval), so nothing runs after it; the only later cleanup,
`prune_merged_worktrees` in `start_change`, removes the worktree with `git worktree remove`
and leaves its branch — on purpose, since `carry-change-in-worktree` excluded branch deletion
because the repository is squash-only (`git branch --merged main` listed only `main`, so
`git branch -d` refuses every merged branch) and forbids force-deleting a branch. Tools that
list branches (VS Code's GitHub Pull Requests view) show every merged PR as still open work.

Observed on the same checkout: for each local branch, `gh pr view <branch> --json
state,headRefOid` against `git rev-parse <branch>` gave 61 `MERGED` with the tip equal to
`headRefOid`, 1 `MERGED` with a different tip, 2 `CLOSED`, 2 without a PR (`main`,
`spike-openspec`). `gh repo view --json deleteBranchOnMerge` is `true`, so the remote side is
already clean.

## What Changes

- `start_change` prunes merged changes in one pass over the local branches: a branch whose PR
  is `MERGED` and whose tip equals that PR's `headRefOid` loses its clean worktree under
  `.claude/worktrees/` and is deleted, with or without a worktree; each removal is printed.
- A merged branch whose tip differs from the PR head, or whose worktree is dirty, is kept and
  named on stderr; the main worktree's branch, the cwd's worktree, and a branch whose PR is not
  merged or absent are left untouched.
- `start_change` prunes `origin`'s remote-tracking refs whose branch is gone.
- A cleanup failure stays a `kept:` line and never fails the start.
- `CLAUDE.md` names this deletion as the one exception to the force-delete prohibition.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: requirement "A change is carried in its own worktree" — its cleanup of
  merged changes also deletes branches at their PR head and prunes stale remote-tracking refs.

## Impact

- Edited: `skills/agent-process/scripts/start_change.py`,
  `tests/publisher/test_start_change.py`, `tests/publisher/delivery_fakes.py`,
  `skills/agent-process/SKILL.md` (Group 0 sentence), `CLAUDE.md` (repository conventions),
  `openspec/specs/implementation/spec.md` (through the delta at archive).
- Added: none. Removed: none.
- `start_change` makes one `gh pr view` call per local branch outside the main worktree and
  the cwd's worktree, instead of one per worktree under `.claude/worktrees/`.
