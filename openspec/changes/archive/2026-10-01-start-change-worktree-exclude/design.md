## Context

`start_change` creates each change's worktree at `<main>/.claude/worktrees/<change>`, inside the
main checkout. git lists a nested worktree as an untracked directory of the enclosing checkout
(observed in a scratch repository with git 2.45.1: `git worktree add .claude/worktrees/x -b x`
then `git status --porcelain` → `?? .claude/`). The publisher hid this with a hand-added
`.git/info/exclude` line; consumers have none (#292).

## Goals / Non-Goals

**Goals:** the main checkout's status stays clean while changes are carried in worktrees, in
new and already-installed consumers alike, with no committed file in the consumer.

**Non-Goals:** moving worktrees out of the checkout (the path is in the spec, `SKILL.md` and
`EnterWorktree` use); cleaning up a gitlink a consumer already committed.

## Decisions

**D1 — `start_change` writes `info/exclude`, not `init` or `.gitignore`.** git's own place for
patterns "specific to a particular repository but which do not need to be shared with other
related repositories" is `$GIT_DIR/info/exclude` (gitignore(5), DESCRIPTION). The path is created by `start_change`, so the step that creates it keeps it
out of status. Alternatives: `init` rendering a marker block into `.gitignore` — visible and
shared by every clone, but `.gitignore` is a file people, framework generators and merges edit
all the time: a broken marker pair stops the next `init` with `Conflict`, and a later `!`
pattern below the block silently re-includes the path; the person chose not to make the
process depend on that file (planning of #292). `init` writing `info/exclude` — `init` runs
once per repository but `info/exclude` belongs to one clone, so a second clone never gets the
line, and a second place knows the worktree path. No new script: one helper in `start_change.py`
beside `WORKTREES`.

**D2 — The file is resolved by git from the main worktree.** `git -C <main> rev-parse
--path-format=absolute --git-path info/exclude`. In the scratch repository both the main
worktree and a linked one under `.claude/worktrees/x` printed the same `<main>/.git/info/exclude`,
so a start from inside a previous change's worktree writes the shared file, and a repository
with a separate git dir is handled by git, not by a joined `.git` path.

**D3 — Idempotent append of `/.claude/worktrees/`.** The line is appended (after a newline
when the file does not end with one; parent created when absent) only when no line of the
file equals it. A consumer that already ignores the path another
way still gets the line — harmless, and simpler than consulting every ignore source.

**D4 — Placement and failure.** The step runs after the worktree listing names `<main>` and
before pruning and `gh issue develop`: a failure (`git rev-parse` non-zero, or an `OSError`
reading or writing the file, re-raised as `RuntimeError` naming the path) is exit 1 before any
branch exists, the same contract as a failed listing. It is not added to the `left` steps,
which start after the branch exists.

## Risks / Trade-offs

- A consumer that relies on seeing `.claude/worktrees/` in status loses that — no use of it is
  known; `git worktree list` remains the listing.
- A gitlink already committed by `git add -A` before this fix is not removed; the exclude
  only prevents new ones.

## Migration Plan

None: the next `start_change` in each consumer writes the line. Rollback is reverting the
helper; the written line is inert without it.
