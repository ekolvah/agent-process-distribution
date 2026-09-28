## Why

After release 3.0.2 a session in this repository got
`agent-process skill not loaded (several installs apply: 3.0.1, 3.0.2)`; the person repaired
`~/.claude/plugins/installed_plugins.json` by hand, the second time (first: session `bbf1d92b`,
2026-09-28 04:51Z) (#256).

**Root cause** (Principle V; observed 2026-09-28, `claude` 2.1.283, `-p` sessions against a
copied plugins root under `CLAUDE_CODE_PLUGIN_CACHE_DIR`, the person's registry untouched):

- A session in a project whose `.claude/settings.json` enables the plugin writes a
  project-scope record keyed by the session's exact cwd string, even when a user-scope record
  exists. A project with no settings, or with only `extraKnownMarketplaces`, gets no record and
  loads the skill from the user record.
- A session started from cmd with `c:\…` beside an existing `C:\…` record wrote a second record,
  the reported duplicate (#256). VS Code passes `c:`, CLI shells `C:`
  (anthropics/claude-code#75855).
- The session loads the **first** record in file order whose path equals the cwd exactly (case
  included) or that is user scope: user 3.0.1 first → 3.0.1 loads; project 3.0.2 first → 3.0.2;
  a `c:` record first with cwd `C:` → skipped. With user 3.0.2 first and a stale `C:` record,
  3.0.2 loaded while our check printed `skill not loaded (several installs apply)`: a false
  alarm.
- Removing `enabledPlugins` from the project leaves an existing project record applying (the
  user-level enable covers it). `claude plugin uninstall … --scope project` run from the
  record's exact spelling removes it and leaves settings alone; from another spelling it exits 1
  (`installed in user scope, not project`) and touches no other repository's record, unlike
  `update` (#90519).

- The user record stays current: in the person's registry the release-3.0.2 auto-update pass
  (2026-09-28 15:05:10Z) moved the user record to 3.0.2, beside the `c:` record of the session's
  cwd, while other repositories' project records stayed behind (sandbox-2 on 3.0.1).

Docs (plugins/install, plugins/loading): project scope is for enabling a plugin for everyone in
a repository, each collaborator still installing it; user scope enables it in every project on
the machine; auto-update "refreshes every marketplace with auto-update on and updates the plugins
installed from them" (plugins/loading, When auto-update runs). Neither page states which record
loads when several apply.

So the duplicates come from our own `enabledPlugins` entry, and the check's `several installs`
verdict does not describe what loads.

## What Changes

- **BREAKING** (consumer machines): Install stops enabling the plugin in the project's
  `.claude/settings.json`; a re-run removes the plugin's `enabledPlugins` entry. The machine gets
  the plugin at user scope: the `plugin-channel` manual row adds `claude plugin install
  agent-process@agent-process-marketplace`.
- This repository's `.claude/settings.json` drops the same entry.
- The skill check requires one enabled user-scope install holding the skill. A project-level
  record of this project is reported under its own headline, `agent-process project-scope install
  applies`, with the exact command removing each record; no user install names the install
  command.
- SKILL.md Install: user scope, no folder-trust precondition, the project-record fix.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: requirements `This repository dogfoods its own process`, `The installed
  footprint is closed`, `A Claude session start reports a missing skill`, `The marketplace follows
  the stable channel`.

## Impact

- Edited: `skills/agent-process/templates/settings.json`, `skills/agent-process/scripts/init.py`
  (`_settings_text`, `plugin-channel` row), `skills/agent-process/templates/skill_check.py`,
  `skills/agent-process/SKILL.md` (Install), `.claude/settings.json`.
- Edited tests: `tests/publisher/test_skill_check.py`, `test_init_remote.py`,
  `test_init_config.py`, `test_plugin.py`, `test_planning_workflow.py`.
- Consumers: each machine runs the `plugin-channel` install once; the check then prints the
  uninstall command for every leftover project record. No installer command touches plugin state.
