## Why

`init --confirm` renders the `quality` hook at `pre-push` in `.pre-commit-config.yaml` but never
installs it: it only prints `manual pre-push`. After a successful confirmed install into the fresh
`ekolvah/ekolvah-agent-process-sandbox-3` (3.2.0, #270), the clone `init` ran in had no
`.git/hooks/pre-push`, so every push ran no local check — silently. The archived design of
`consumer-pre-push-hook` (*Risks*) accepted exactly this gap.

**Root cause:** the per-clone step was made manual wholesale because unsetting `core.hooksPath`
changes the git config every worktree shares. That reason holds only when `core.hooksPath` is
set; in the observed clone it was unset and `pre-commit` was on `PATH`, so nothing stood in the
way. Clones other than the one `init` runs in have no carrier at all: nothing tells the person
there that the hook is missing.

**Observed** (pre-commit 4.6.0, scratch repositories, 2026-09-30):

- `pre-commit install --hook-type pre-push` in a repository with no `.pre-commit-config.yaml`
  prints `pre-commit installed at .git\hooks\pre-push`, exits 0, and the hook carries
  `# ID: 138fd403232d2ddd5efb44317e38bf03` (the line `manual.py` already reads); a second run
  prints the same and exits 0.
- Over an existing foreign `.git/hooks/pre-push` it prints `Running in migration mode with
  existing hooks at .git\hooks\pre-push.legacy`, exits 0.
- With `core.hooksPath` set it prints `[ERROR] Cowardly refusing to install hooks with
  core.hooksPath set.` and exits 1.

## What Changes

- `init` gains a `pre-push` transition after `onboarding-pr`: `unchanged` when this clone already
  runs pre-commit's pre-push hook, `planned` when it does not, `core.hooksPath` is unset and
  `pre-commit` is on `PATH`. A confirmed run performs it with `pre-commit install --hook-type
  pre-push` in the clone; it writes only this clone's git hooks and commits nothing. A planned
  `pre-push` alone starts no onboarding branch, commit, issue, push or PR.
- When `core.hooksPath` is set or `pre-commit` is not on `PATH`, no `pre-push` transition is
  printed and the `manual pre-push` row stays, now naming that reason. The row is no longer
  printed for a clone the run installs (or would install).
- The installed `SessionStart` check (`.claude/agent-process-check.py`) also prints a visible
  marker, `agent-process pre-push hook not installed`, with the reason and both commands, when
  the project's `.pre-commit-config.yaml` carries the agent-process block and this clone does not
  run pre-commit's pre-push hook — the carrier for every other clone.
- Out of scope: changing `core.hooksPath` automatically.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: *The installed footprint is closed* admits this clone's pre-push hook;
  *Init renders the pre-push hook* gains the `pre-push` transition and narrows the manual row to
  a blocked clone; new *A Claude session start reports a missing pre-push hook*.

## Impact

- Edited: `skills/agent-process/scripts/init.py` (the `pre-push` step, docstring step list),
  `skills/agent-process/scripts/manual.py` (one reader of the clone's pre-push state for the step
  and the row), `skills/agent-process/templates/skill_check.py` (the pre-push marker),
  `skills/agent-process/SKILL.md` (Install step 4: the `pre-push` row).
- Edited tests: `tests/publisher/init_harness.py` (`LABELS`, an injectable `which`),
  `tests/publisher/test_init_remote.py`, `tests/publisher/test_skill_check.py`.
- Added / removed: none. No ADR: the decision is local to the installer and recorded in
  `design.md`.
