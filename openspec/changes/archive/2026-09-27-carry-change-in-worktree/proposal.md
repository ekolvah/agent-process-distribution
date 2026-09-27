## Why

Two agents cannot carry two changes at once in one repository (#236): they share one
checkout, and the delivery start moves that checkout under the other agent's feet.

Reproduction (observation, this repository): agent A proposes change `a` on `main` —
`openspec/changes/a/` is untracked in the shared checkout. Agent B runs Group 0 of change `b`:
`start_change.py` calls `gh issue develop -c <N> --name b`
(`skills/agent-process/scripts/start_change.py:152`), which checks `b` out **in the shared
checkout**. A's untracked `openspec/changes/a/` and any uncommitted edit of A now sit on
branch `b`; A's next edit lands on B's branch, and B's `archive_change.py` refuses the dirty
worktree (`archive_change.py:84`) or B commits A's files.

Root cause: the delivery start assumes one checkout per repository — the branch of a change
is checked out in place instead of in a working tree of its own.

Platform behaviour this plan rests on (observed):

- `gh issue develop --help` (gh on this machine): `-c, --checkout  Checkout the branch after
  creating it` — without `-c` the linked branch is created on the remote and nothing is
  checked out.
- `git worktree add -h` (git 2.45.1): `-b <branch>  create a new branch` and `--[no-]track
  set up tracking mode`.
- Claude Code `EnterWorktree` tool description: "Pass `path` instead of `name` to switch the
  session into a worktree that already exists (e.g., one you just created with `git worktree
  add`) … the path must appear in `git worktree list`", and "ExitWorktree will not remove a
  worktree entered this way".
- `.claude/worktrees/` is already excluded here (`git check-ignore -v .claude/worktrees/x` →
  `.git/info/exclude:14:**/.claude/worktrees/`).

## What Changes

- `start_change.py` creates the linked branch without checking it out, adds a worktree for it
  at `.claude/worktrees/<change>` of the main worktree (wherever it runs) tracking `origin/<change>`, and moves the untracked
  `openspec/changes/<change>/` into that worktree. The shared checkout keeps its branch and
  every other file.
- Group 0 enters that worktree (`EnterWorktree` with its `path`); every later task of the
  apply runs there. A run interrupted before the archive resumes by entering the same
  worktree; a failure after the branch exists names the remaining steps starting with the
  worktree, not `git switch`.
- No manual cleanup: every `start_change` first removes the worktrees of changes whose PR is
  merged (clean ones; a dirty one is kept and named), so the next change cleans up after the
  previous ones.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: the linked branch is created without checkout and carried in its own
  worktree; Group 0 enters it (requirements "GitHub links branch, PR and issue", "Delivery
  steps are tasks of every change"; added "A change is carried in its own worktree").

## Impact

- Edited: `skills/agent-process/scripts/start_change.py`, `skills/agent-process/SKILL.md`
  (Group 0), `tests/publisher/test_start_change.py`,
  `tests/publisher/delivery_fakes.py` (the fake answers `git fetch`, `git worktree add`, `git worktree list --porcelain` and `gh pr view` through a `pr_states` mapping, lists `extra_worktrees`, and can pass `git` to a real runner via `git_runner`),
  `tests/publisher/test_planning_workflow.py` if it asserts the Group 0 wording.
- Specs: `openspec/specs/implementation/spec.md` through the delta.
- Consumers: the script and skill ship in the plugin; no installer change.
- No ADR: a local mechanism change of one script, no alternative with lasting consequences
  beyond `design.md`.
