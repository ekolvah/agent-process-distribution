## Why

The worktree `start_change` creates for a change sits inside the main checkout and shows there
as untracked, so the main checkout is never clean while a change is in flight, and `git add -A`
there stages the worktree as an embedded repository (#292).

**Observation:** on `ekolvah/agent-process-sandbox-4` (installed with 3.2.2) after the first
change's `start_change`, `git status --short` of the main checkout printed
`?? .claude/worktrees/` (issue #292). A scratch repository with git 2.45.1 reproduces it: after
`git worktree add .claude/worktrees/x -b x`, `git status --porcelain` printed `?? .claude/`.

**Root cause:** `start_change` places every worktree at `<main>/.claude/worktrees/<change>`
(`skills/agent-process/scripts/start_change.py`, `WORKTREES` and the `git worktree add` call),
and nothing in `start_change`, `init`, `steps.py` or `onboarding.py` keeps that path out of the
main checkout's status. This publisher never showed the defect because its own
`.git/info/exclude` carries a hand-added `**/.claude/worktrees/` line
(`git check-ignore -v .claude/worktrees/x` → `.git/info/exclude:14:**/.claude/worktrees/`).
The test `test_parallel_changes` asserts the defect: it expects the start's new status lines to
be `?? .claude/…`.

**Reproduction:** `start_change` on a real clone (the `_clone` fixture of
`tests/publisher/test_start_change.py`) leaves `git status --porcelain` of the main checkout
non-empty. This becomes the RED test.

## What Changes

- Before it creates the branch, `start_change` ensures the line `/.claude/worktrees/` is in the
  repository's `info/exclude` (resolved by git from the main worktree, so a start from inside a
  previous change's worktree writes the same file); it appends the line only when absent. No
  committed file of the consumer changes, and a consumer installed earlier heals on its next
  `start_change`.
- `test_parallel_changes` stops asserting the defect: the start adds no status line to the
  checkout it runs in.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: *A change is carried in its own worktree* — the worktrees under
  `.claude/worktrees/` do not show in the main worktree's status.

## Impact

- Edited: `skills/agent-process/scripts/start_change.py` (exclude step before `gh issue
  develop`; docstring).
- Edited tests: `tests/publisher/test_start_change.py` (new `test_main_checkout_stays_clean`;
  `test_parallel_changes` assertion), `tests/publisher/delivery_fakes.py` (the fake answers
  `git rev-parse --git-path info/exclude`).
- Added / removed: none. No ADR: no decision of record changes. `SKILL.md` is unchanged: no
  agent step changes, and the spec carries the new behaviour.
