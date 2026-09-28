## Why

Issue #253. Reproduction, observed 2026-09-28 driving `add-greet-function` through release
3.0.0 in `ekolvah/agent-process-sandbox-2` (issue #3, PR #4 there): SKILL.md prints every script
as `python skills/agent-process/scripts/<script>.py`, the `tasks` rule has the planner copy those
commands into `tasks.md`, and in a consumer repository that path does not exist — the scripts
live in the plugin cache `~/.claude/plugins/cache/agent-process-marketplace/agent-process/3.0.0/`.
Every task command of the consumer's `tasks.md` (`start_change.py`, `check_red.py`,
`archive_change.py`, `wait_for_pr.py`) is non-runnable as written; the agent translates each one
into the only path it can resolve, which is pinned to a release the auto-update later removes.

Root cause: the skill has no runnable, version-independent way to address its own scripts from a
consumer root. The publisher test `test_printed_commands_run_as_printed` encodes the gap — "No
script is on `PATH`: a printed command names … a file that exists" — checked against the
publisher's own tree only.

Platform behaviour, observed:
- code.claude.com/docs/en/plugins-reference, "Standard layout": "`bin/` — Files here are on the
  Bash tool's `PATH` while the plugin is enabled, so Claude runs them as bare commands." The
  Bash tool of this session (Claude Code 2.1.283) has
  `/c/Users/jadow/.claude/plugins/cache/agent-process-marketplace/agent-process/3.0.1/bin` on its
  `PATH` (`echo "$PATH"`), for a release that has no `bin/` yet.
- Same page, "Where each variable resolves": "The variables aren't present in the environment of
  commands Claude runs through the Bash tool"; in skill content `${CLAUDE_PLUGIN_ROOT}` is
  substituted inline with the "Absolute path of the plugin's installed version" — the pinned path
  the issue rules out. `echo ${CLAUDE_PLUGIN_ROOT-unset}` in the Bash tool printed `unset`.
- The manifest has no key that moves `bin/` (the Fields table lists `commands`, `agents`,
  `outputStyles`, … — no `bin`), so it lives at the plugin root.
- In Git Bash (Windows 11) an extensionless `#!/bin/sh` file on `PATH` ran as a bare command with
  LF and with CRLF endings (`agent-process hello x y` → `ran ['x', 'y']`, exit 0); the plugin
  cache on this machine holds CRLF files (`file …/3.0.1/skills/agent-process/SKILL.md`).
- This machine's marketplace (`known_marketplaces.json`) was added by the `plugin-channel` row
  without `sparsePaths`: a full clone, so a root `bin/` reaches it on the next update. A clone
  added fresh from project settings is sparse (ship-only-distributed-paths proposal), and a known
  marketplace is not re-cloned by a changed settings entry (#184).

## What Changes

- The plugin ships one executable, `bin/agent-process`: `agent-process <script> [args]` runs
  `python <script>.py` from the repository's own `skills/agent-process/scripts/` when the current
  directory has one (the publisher checkout, exempt from release drift), otherwise from the
  plugin's own skill directory. An unknown or missing script name exits 2 listing the names.
- SKILL.md prints every script command as `agent-process <script> …`, run through the Bash tool;
  the Install sentence that asks the agent to translate `skills/agent-process/` goes away.
- `archive_change` ticks its own task in either form, `agent-process archive_change <change>` or
  the old `archive_change.py <change>` of an in-flight `tasks.md`.
- The marketplace clone is whole again: the rendered marketplace source and this repository's
  settings drop `sparsePaths` (ship-only-distributed-paths, #216). A sparse set is frozen on
  every machine that cloned with it (#184), so each new component root — `bin/` is the first —
  would miss those machines, while the two carriers already disagree: the `plugin-channel` row
  adds the marketplace whole, a first add from project settings adds it sparse. What sparse
  bought is about 2.6 MB of development tree per cached release (#216 records no harm beyond
  that); the plugin loader reads only component roots, so the guard that matters becomes a
  closed list of the repository's top-level component roots.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: skill commands run from a consumer root (ADDED); the plugin's component
  roots are closed (ADDED); the marketplace fetches only the package (REMOVED).

## Impact

- Added: `bin/agent-process` (git mode 100755).
- Edited: `skills/agent-process/SKILL.md`, `skills/agent-process/scripts/archive_change.py`
  (`_mark_own_task`), `skills/agent-process/templates/settings.json` and `.claude/settings.json`
  (`sparsePaths` removed), `tests/publisher/test_planning_workflow.py`,
  `tests/publisher/test_plugin.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/test_pr_delivery.py`, `openspec/specs/distribution/spec.md` (by archive).
- Removed: none. Not edited: the scripts' `Usage:` docstrings and the absolute resume lines
  `start_change`/`create_tracking_issue` print at runtime — they are read, not copied into
  `tasks.md`, and resolve as printed.
- Consumer machines: a marketplace added sparse from project settings since 2.7.0 stays sparse
  (#184) and lacks `bin/`; `agent-process` then fails visibly with `command not found`. Removing
  and adding the marketplace again is the expected recovery — inferred, not observed (design.md,
  Risks). A consumer's re-run Install renders the source without `sparsePaths`.
