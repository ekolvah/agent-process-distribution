## Context

`start_change` already cleans up after merged changes at the start of the next one:
`main_worktree` calls `prune_merged_worktrees`, which asks `gh pr view <branch> --json state`
for each worktree under `.claude/worktrees/` and runs `git worktree remove` on a merged, clean
one. `carry-change-in-worktree` (design, Non-Goals) kept the branch: squash merges are never
"merged" for `git branch -d`, and `CLAUDE.md` forbids force-deleting a branch. The git guard
that once denied `git branch -D` was removed (ADR 0040, D5); the prohibition is prose only.

## Goals / Non-Goals

**Goals:** a merged change leaves no local branch, worktree or stale remote-tracking ref
after the next `start_change`; no branch carrying work outside its merged PR is lost.

**Non-Goals:** remote branches (`deleteBranchOnMerge` already removes them); branches whose PR
was closed unmerged (2 observed — work the person may still want; they stay); a separate
cleanup command or a scheduled job.

## Decisions

**D1 — Delete only a tip equal to the merged PR's `headRefOid`.** The read becomes
`gh pr view <branch> --json state,headRefOid`; the branch is deleted when `state` is `MERGED`
and `git rev-parse <branch>` equals `headRefOid`. That tip is exactly the commit GitHub
squashed into `main`, and it stays fetchable from `refs/pull/<N>/head`, so the deletion loses
nothing that is not on GitHub. A commit after merge, or a branch name reused from a fresh
`main` (the squash commit's SHA differs from every PR head), fails the comparison and keeps
the branch. *Observed:* for a name reused by several PRs, `gh pr view
release-please--branches--main --json number,state` answered `{"number":435,"state":"MERGED"}`,
the most recently updated of five merged PRs (gh 2.87.3); the comparison does not depend on
which PR gh picks, since an older PR's head never equals a tip that moved on.
*Observed:* `git ls-remote origin refs/pull/434/head` gives `001e7fff94efb71c1f71dc7075a0ede41bbe79f4`,
the `headRefOid` of merged PR #434 — a merged head stays fetchable.
*Alternatives:* `git branch -d` — refuses every squash-merged branch (`git branch --merged
main` listed only `main`); upstream `gone` as the signal — it says the remote branch is
deleted, not that its work is merged, and a closed unmerged PR's branch is deleted too.

**D2 — `git branch -D` behind D1, and `CLAUDE.md` names the exception.** The prohibition
exists so that unmerged work is not destroyed; D1 is that check made executable, run by a
script under test instead of judged by the agent. `git update-ref -d refs/heads/<b> <oid>` —
a compare-and-delete — was rejected: it skips git's own refusal for a checked-out branch and
leaves the `branch.<b>.*` config section behind. The convention line in `CLAUDE.md` gains the
exception "except a merged branch at its PR head, which `start_change` deletes".

**D3 — One loop over branches; the worktree is the branch's attribute.**
`prune_merged_worktrees` becomes `prune_merged_changes`, iterating `git for-each-ref refs/heads
--format='%(refname:short)%00%(objectname)%00%(worktreepath)'` — name, tip and checkout in one
call. *Observed* on git 2.45.1.windows.1: the format prints NUL-separated fields, the
worktree path absolute with forward slashes (`C:/Users/.../.claude/worktrees/<b>`), so it is
resolved as a `Path` before the comparison with `.claude/worktrees/`. A branch checked out outside
`.claude/worktrees/` (the main worktree's `main`) or in the worktree containing the cwd is
skipped before any `gh` call; otherwise one `gh pr view` decides both steps: worktree removal
(when clean) and branch deletion. The worktree predicate tightens from "PR merged" to D1's
"tip is the merged PR's head" — a merged worktree with commits after the merge is now kept and
named instead of removed. Merged branches that never had a worktree are covered. *Alternatives:*
a second loop after the worktree loop — two PR reads per removed worktree and two predicates;
one bulk `gh pr list --state merged --json headRefName,headRefOid` — one call, but `--limit`
truncates, and a branch past it would stay unnoticed; per-branch reads cost one round trip per
remaining local branch, a handful once the backlog is gone.

**D4 — `git remote prune origin` for stale refs.** It deletes only remote-tracking refs whose
branch is gone on `origin`, without downloading objects, which is the whole job. *Observed* on a scratch clone whose `origin` had deleted `gone`:
`git remote prune origin` printed `* [pruned] origin/gone`, and afterwards `git branch -r`
listed only `origin/main` while the local `gone` remained;
`git fetch --prune` would also fetch everything, and setting `fetch.prune` would change the
person's git configuration.

**D5 — Same failure contract as the worktree loop.** A `gh` or `git` failure on one branch,
or of the prune, is a `kept: <branch|origin> — <error>` line on stderr and the loop goes on;
`no pull requests found` stays silent, as today. A merged branch whose tip differs is
`kept: <branch> — tip is not the merged PR's head`, so the person sees it each start
(§IV) instead of the branch silently surviving.

## Risks / Trade-offs

- [The person keeps working on a branch after its PR merged, without committing] → nothing
  lost: uncommitted work lives in a worktree, and a dirty worktree keeps its branch (D3).
- [A merged branch with later commits is reported every start] → intended visibility; the
  person deletes or reopens it.
- [Consumers whose own instructions forbid force-deleting a branch] → the deletion is the
  process script's, not the agent's command; `CLAUDE.md` is this repository's, and a
  consumer's rule is theirs to amend.

## Migration Plan

No migration: the first `start_change` after release removes the backlog of every checkout
that runs it. Rollback is reverting the PR; a deleted branch is restored with
`git fetch origin pull/<N>/head:<branch>`.
