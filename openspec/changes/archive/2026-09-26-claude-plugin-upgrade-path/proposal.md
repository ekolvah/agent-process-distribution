## Why

The fix the process names for a Claude skill older than the project's release does not move
the machine (#184). `## Install` and the skill-behind message of `start_change.py` and
`create_tracking_issue.py` (`release_drift` in `skills/agent-process/scripts/init.py`) both say
`/plugin marketplace update agent-process-marketplace` and a restart.

Observed on Claude Code 2.1.283, 2026-09-26, with the tables and exact outputs in
[#184 comment 5844804395](https://github.com/ekolvah/agent-process-distribution/issues/184#issuecomment-5844804395)
and [#184 comment 5844817104](https://github.com/ekolvah/agent-process-distribution/issues/184#issuecomment-5844817104):

- `marketplace update` clones the ref the machine already holds (`Cloning … (ref: v0.1.1)`),
  also when run in a project whose `.claude/settings.json` declares another ref. A session start
  in that project does not re-point it either.
- Session start follows the **user-scope** declaration (`extraKnownMarketplaces` in
  `~/.claude/settings.json`). `claude plugin marketplace add "<repo>#v<x.y.z>"` writes that
  declaration only while no settings declare the name. Once one exists it refuses: `its network
  source differs from the one declared for it in settings … change the declaration`.
- Moving the marketplace does not move an install. `claude plugin update
  agent-process@agent-process-marketplace --scope project` then prints `updated from 2.0.0 to
  0.1.0 … Restart to apply changes`.

Root cause: the process assumed a per-name marketplace follows the ref the project declares.
It follows the user-scope declaration, and installs follow the marketplace only through an
explicit `plugin update`.

## What Changes

- The skill-behind message of the release-drift check names the observed path to release
  `<recorded>`: declare `ref: v<recorded>` at user scope (`claude plugin marketplace add
  "ekolvah/agent-process-distribution#v<recorded>"`, or edit the existing declaration in
  `~/.claude/settings.json`), restart, run `claude plugin update
  agent-process@agent-process-marketplace --scope <scope>` for each install, and restart. For
  Codex the message still says: Install with `--version <recorded>`.
- `## Install` replaces `/plugin marketplace update` with the same path and states that the
  user-scope declaration pins the release for every repository on the machine.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the release-drift fix for a skill behind the project names the user-scope declaration and the plugin update instead of a marketplace update.

## Impact

- Edited: `skills/agent-process/scripts/init.py` (`release_drift` message),
  `skills/agent-process/SKILL.md` (`## Install`), `tests/publisher/test_start_change.py`
  (`_SKILL_FIX`), `tests/publisher/test_planning_workflow.py`
  (`test_install_names_the_skill_marker`).
- Added, removed: none.
- `.agent-process/docs/adr/0011-agentic-process-distribution-mechanism.md` keeps its
  `/plugin marketplace update` line. It records the v1 decision to use the marketplace, not the
  upgrade procedure.
- A machine still on a skill without this change prints the old fix. The corrected message
  reaches a person only once the skill carries it, from the first release after this change.
