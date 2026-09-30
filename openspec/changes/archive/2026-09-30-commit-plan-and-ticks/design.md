## Context

See proposal.md — Why. `start_change` marks nothing and commits nothing; `archive_change` already marks its own task (`_mark_own_task`) before `openspec archive` and commits with
`git add -A openspec`. The pre-push hook runs the quality command on a push, not on a commit.

## Goals / Non-Goals

**Goals:** every commit before the archive is named by the process; no improvised commit is
needed to reach a worktree `archive_change` accepts.

**Non-Goals:** pushing the plan commit (the archive push carries it); a check of the commit
history (RED order stays the implementer's rule and `check_red`'s proof).

## Decisions

### D1 — `start_change` commits the plan, its own task ticked

After the move, `start_change` ticks the Group 0 task item naming `start_change <change>` in
the moved `tasks.md` (the same item matcher `archive_change` uses, shared, keyed by the script
name), then runs `git -C <worktree> add openspec/changes/<change>` and
`git -C <worktree> commit -m "chore: plan <change>"`. The commit is a step of the `left` list
between the move and `set_status`, so a failure (no git identity, a consumer commit hook) names
it and the steps after it. No push: the branch's first push is the archive's, and a push here
would run the pre-push quality command on a plan without code.

Alternatives: a rule telling the implementer to commit the plan — the prose that the
observation shows is not followed (it made up `docs: … plan`); committing in the propose run on
`main` — the propose run has no branch and the plan must not land on `main`.

### D2 — `archive_change` tolerates only the change's own `tasks.md`

The clean check keeps every `git status --porcelain` line except one whose path is exactly
`openspec/changes/<change>/tasks.md` with a modification status (`XY` from ` M`, `M `, `MM`;
git-status(1), "Short Format": each line is `XY PATH`). Anything else — another file, an
untracked path, that `tasks.md` deleted — still exits 2 and is printed. The archive moves that
`tasks.md` and `git add -A openspec` stages it, so the ticks ride in the archive commit.

This drops part of a guard; per SKILL.md#design:
- New input: the uncommitted `tasks.md`. Failure mode: it holds edits beyond ticks.
- What stops proving: that `tasks.md` equals its last group commit at the archive.
- What still proves the guarded invariant — nothing is left behind the pushed head: the
  remaining check (every other path) and `git add -A openspec` in the same script; the pushed
  archive head, whose diff the `agent-review` job reads on the PR, carries any such edit.

Alternative: a rule "the Verify group ends with a commit of its ticks" — the extra commit
(`chore: … verified`) the observation shows as improvised, kept as prose.

### D3 — SKILL.md states the tick commits

`SKILL.md` Tasks: Group 0's tick is `start_change`'s; Group 1 commits RED with its ticks; each
implementation group's commit carries its ticks; Verify's ticks ride in the archive commit.
`SKILL.md` Delivery: start from a worktree clean but for the change's `tasks.md`. No new
script; the scripts' docstrings follow.

## Risks / Trade-offs

- [A consumer without git identity in the worktree] → the commit step fails after the move;
  `start_change` exits 1 naming the commit and the later steps (D1).
- [The RED commit is no longer the first commit of the branch] → the RED requirement and its
  scenario now name the plan commit as its predecessor; nothing reads commit order.

## Migration Plan

Ships with the next plugin release. No change is started (`git worktree list` prints the main
worktree alone). A planned change started by the old `start_change` and archived by the new
`archive_change` still meets exit 2 on its untracked plan, named, as today; committing that
plan by hand is the fix.
Rollback: revert the PR; the old scripts ignore the plan commit.
