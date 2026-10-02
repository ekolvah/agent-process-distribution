## Why

`create_tracking_issue` and `start_change` validate `architect-review.json` with `jsonschema`,
imported in the interpreter the launcher picks (`bin/agent-process:30`, `exec python "$file"`).
A consumer whose `python` lacks the package stops at the end of its first propose run (issue
#309, observed 2026-10-02 in `ekolvah/kinozal_scraper`, plugin 3.2.8, `.venv` Python):

```
$ agent-process create_tracking_issue otel-project-label
Error: architect review not validated: No module named 'jsonschema'
```

Root cause: the plugin runs its scripts in whatever `python` the session finds and never
installs what they import. Its runtime manifest exists (`.agent-process/requirements.txt`,
pinned, pip-audited), but only this repository's CI installs it.

## What Changes

- The plugin installs `.agent-process/requirements.txt` into a virtual environment in its data
  directory (`${CLAUDE_PLUGIN_DATA}`) from a `SessionStart` hook, on first run and whenever the
  manifest changes — the pattern Claude Code documents for plugin dependencies
  ("Install dependencies into the data directory").
- The hook exports `AGENT_PROCESS_PYTHON`, that environment's interpreter, through
  `CLAUDE_ENV_FILE`; the launcher runs every script with it, falling back to `python`.
- A failed install prints an `agent-process plugin environment not installed` marker to the
  person and the agent, and is retried next session.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the plugin installs and selects its own runtime environment; the
  adopted-repository gate applies to the tool hooks, not to that install.

## Impact

- Added: `skills/agent-process/scripts/plugin_env.py`.
- Edited: `hooks/hooks.json` (a `SessionStart` entry), `bin/agent-process` (interpreter),
  `skills/agent-process/SKILL.md` (Install), `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`
  (the prerequisite sentence), `tests/publisher/test_plugin.py`,
  `tests/publisher/test_start_change.py` (closed script set).
- No new dependency and no new manifest: the plugin installs the one this repository already
  pins and audits. Installed consumers get the hook with the plugin's auto-update; nothing is
  rendered into a consumer.
