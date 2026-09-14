## Why

v1 delivers the process by copying files into consumers through a Copier mirror, which
needs drift tests, an adoption CLI and three-way merges on update. Claude Code plugins,
Codex skill directories and GitHub reusable workflows are native delivery channels with
native update commands.

## What Changes

- Claude Code plugin (marketplace = this repository) with skills, the `architect-reviewer`
  agent, hooks, rules and a deny-list; Codex skills from an updateable checkout; reusable
  workflow `agent-process.yml@v2` with Dependabot bumps.
- `/agent-process:init` creates the whole consumer footprint, including `openspec init`.
- Ruleset JSON kept here and installed once by `init`.
- **BREAKING**: `template/`, `template_drift.py`, `adopt_agent_process.py`,
  `template-drift-allowlist.yml` and their tests are deleted.

## Capabilities

### New Capabilities
- `distribution`: how the process is installed, updated and extended.

### Modified Capabilities
- `implementation`: adds `ci_check` on every push, shift-left hooks, Stop hook, principles
  via plugin rules.
- `review-and-merge`: adds the GitHub-native merge gates and the local deny-list (the
  capability is new here; review behaviour arrives with `v2-4-review-and-state`).
- `maintenance`: adds versioning by tag.

## Impact

- Added: `.claude-plugin/plugin.json`, `marketplace.json`, `hooks/`, `rules/principles.md`,
  `settings.json`, `.github/workflows/agent-process.yml`, `ruleset.json`, `commands/init.md`.
- Removed: Copier mirror and adoption CLI (≈ 4 000 lines with tests).
