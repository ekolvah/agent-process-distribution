## Why

#187, observed in `ekolvah/agent-process-sandbox` after `init --confirm` (#117 step 7a): the
Claude plugin cache held 0.1.0 (#184) — no `SKILL.md`, no `scripts/`. `/opsx:propose` ran, nothing
said the skill was absent, and the agent cloned the `v2.0.0` tag into its scratchpad and ran
scripts from there. In this repository the plugin did not load for about three weeks (a stale
user-scope marketplace entry) and no session noticed. The agent sees the skill is missing and
improvises; the person sees nothing.

Root cause: nothing the installer leaves in a consumer runs when the plugin is absent, so the
absence has no carrier to the person. The agent is the only witness, and it is built to finish
the task.

Observation (#187 comments, 2026-09-26, Claude Code 2.1.280): a `SessionStart` hook in the
project's `.claude/settings.json` runs with the plugin disabled, headless and interactive; its
`hookSpecificOutput.additionalContext` reaches the agent and its `systemMessage` is shown to the
person in the interactive UI; a crashing hook is silent. The hook's
input carries nothing about loaded plugins; `claude plugin list --json` (0.5 s) reports, per
project, each install's `enabled`, `version` and `installPath`, and can list several project
entries for one folder that differ only in drive-letter case. Codex runs a project hook only
after an interactive per-hook approval, and its skill is the user-wide link `init` itself
creates: Codex is out of scope.

## What Changes

- `init` installs `.claude/agent-process-check.py` and one owned `hooks.SessionStart` entry in
  `.claude/settings.json` that runs it.
- At every Claude session start the check reads `claude plugin list --json` and passes only when
  exactly one enabled install of the plugin applies to the project and it holds
  `skills/agent-process/SKILL.md`. Otherwise — or on any error of its own — it shows the person
  `agent-process skill not loaded (<reason>) — fix: <Install URL>` and tells the agent not to
  reconstruct the skill.
- `## Install` names the marker and its fixes.
- The installed footprint grows by that file and that hook entry. This repository runs the same
  check from its source.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the installed footprint gains the skill check, and a Claude session start reports a missing skill.

## Impact

- Edited: `.claude/settings.json`, `skills/agent-process/SKILL.md`, `skills/agent-process/scripts/init.py`,
  `skills/agent-process/templates/settings.json`, `tests/publisher/test_init.py`,
  `tests/publisher/test_plugin.py`, `tests/publisher/test_planning_workflow.py`.
- Added: `skills/agent-process/templates/skill_check.py`, `tests/publisher/test_skill_check.py`.
  Removed: none.
- Consumers get the check on their next `init --confirm`; one whose settings file is hand-formatted
  gets the existing conflict with a manual instruction. Release drift is #190.
