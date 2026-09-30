## Why

Observed on 2026-09-28 (#252) driving `add-greet-function` through release 3.0.0 in
`ekolvah/agent-process-sandbox-2` (PR ekolvah/agent-process-sandbox-2#4): right after
`start_change`, `git status -sb` in `.claude/worktrees/add-greet-function` showed
`?? openspec/changes/add-greet-function/`. `start_change.py` moves the plan into the worktree
and commits nothing; `archive_change.py` exits 2 when `git status --porcelain` is not empty
(`archive_change.py:87-94`). The implementer made up two commits no rule names,
`docs: add-greet-function plan` and `chore: add-greet-function verified`, and held the Group 1
ticks back so the RED commit would hold only the tests and stub.

Root cause: the delivery procedure requires a clean worktree at the archive but assigns
neither the commit of the plan nor the commit of the ticks made before it.

## What Changes

- `start_change` ticks its own Group 0 task in the moved `tasks.md` and commits the plan on
  the change branch (`chore: plan <change>`, not pushed), leaving the worktree clean; a
  failure after the move names the commit among the steps left.
- `archive_change` accepts a worktree whose only change is the change's own `tasks.md` —
  ticks made after the last group commit — and its archive commit carries them; any other
  change still exits 2.
- `SKILL.md` Tasks: the commit that ends a group carries that group's ticks (the RED commit
  carries Group 1's); ticks after the last group commit ride in the archive commit.
  `SKILL.md` Delivery states the same precondition.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `implementation`: *RED first for behavioural changes* (the RED commit follows the plan
  commit and carries the Group 1 ticks), *A change is carried in its own worktree* (the plan
  is committed there), *`archive_change` archives the change before its PR* (the change's
  own `tasks.md` is the one tolerated change).

## Impact

- Edited: `skills/agent-process/scripts/start_change.py`,
  `skills/agent-process/scripts/archive_change.py`, `skills/agent-process/SKILL.md`,
  `tests/publisher/test_start_change.py`, `tests/publisher/test_pr_delivery.py`,
  `tests/publisher/test_planning_workflow.py`, `tests/publisher/delivery_fakes.py`.
- ADR: none — a fix inside the existing delivery decision; `design.md` records D1–D3.
- Added: none. Removed: none.
- Consumers get the behaviour with the next release of the plugin. No change is started:
  `git worktree list` prints the main worktree alone. Three planned changes
  (`check-red-collection-hint`, `hermetic-sandbox-push`, `init-failed-command-output`) will be
  started by whichever release the machine has; one started before the upgrade and archived
  after it meets the exit 2 on its untracked plan, as today (design.md — Migration Plan).
