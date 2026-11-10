## Why

A consumer learns that its repository files lag the installed plugin only when `start_change` or
`finish_propose` exits 2 on release drift — mid-work, at the start of the next change. The plugin
updates itself through `stable` and auto-update; the repository files have no trigger.

Observed on this machine (2026-11-10): `claude plugin list --json` lists
`agent-process@agent-process-marketplace` at user scope with `"version": "3.29.2"`, while
`../Lampa/openspec/config.yaml` records `# agent-process release: 3.29.0` and
`../kinozal_scraper/openspec/config.yaml` records `3.16.0`. Both sessions start silent.

The repository's skill check (`.claude/agent-process-check.py`) is the copy `init` wrote, so in
exactly these repositories it is the old copy; the plugin's own `SessionStart` hook
(`plugin_env.py session-start`) runs from the plugin cache and updates with the plugin.

## What Changes

- The plugin's `SessionStart` hook, in a project whose `openspec/config.yaml` holds the
  agent-process block, runs the drift comparison of `start_change` (`init.release_drift`) and
  prints its message as the marker `agent-process release drift`. No network call.
- The drift message names `/agent-process:init` for a project behind the skill, in the session
  marker and in `start_change`/`finish_propose` alike. `start_change` stays the backstop.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: a new requirement — a Claude session start reports release drift.

## Impact

- Edited: `skills/agent-process/scripts/plugin_env.py` (drift reader, joined marker output, docstring).
- Edited: `skills/agent-process/scripts/init.py` (`release_drift` names `/agent-process:init`).
- Edited: `tests/publisher/test_plugin.py`, `tests/publisher/test_start_change.py`.
- Edited: `skills/agent-process/SKILL.md` (Install: the session-start markers) and
  `tests/publisher/test_planning_workflow.py` (the marker is not a launcher call).
- Edited: `openspec/specs/distribution/spec.md` (via the archived delta).
- No ADR: the hook, the comparison and the backstop already exist.
