## Why

The navigation policy — PreToolUse hooks that deny shell navigation (`cat`, `grep`, `find`,
`sed -n`, …) and whole-file `Read` over the budget, naming the cheaper tool — acts only in this
repository: its code lives in publisher-only `.agent-process/scripts/` and is wired in this
repository's own `.claude/settings.json`. Consumers get none of it, so each keeps a hand-copied
version (ekolvah/kinozal_scraper, where the parser originated) or none (#310). The plugin is the
process's carrier into every consumer, and Claude Code merges a plugin's `hooks/hooks.json` with
the user's and project's hooks ([hooks reference](https://code.claude.com/docs/en/hooks): "When a
plugin is enabled, its hooks merge with your user and project hooks.").

The plugin is installed at user scope (archived change `2026-09-28-user-scope-plugin`, forced by
anthropics/claude-code#75855, still open), so a plugin hook fires in every repository on the
machine, adopted or not. A hook shipped without a gate would deny `cat` in an unrelated project.

## What Changes

- `navigation_policy.py` moves into the package (`skills/agent-process/scripts/`) together with the
  `pre-bash`/`pre-read` adapters now in `.agent-process/scripts/hooks.py`; it becomes a launcher
  script `agent-process navigation_policy pre-bash|pre-read`.
- New plugin component root `hooks/` with `hooks/hooks.json`: PreToolUse matchers `Bash` and
  `Read` run the policy through the plugin's launcher.
- Adoption gate: every plugin hook command exits 0 with no output when
  `$CLAUDE_PROJECT_DIR/.github/workflows/agent-process.yml` (the workflow `init` installs) is
  absent.
- This repository's `.claude/settings.json` drops its PreToolUse `Bash`/`Read` entries — the
  plugin delivers them; the on-edit PostToolUse hook stays.
- SKILL.md Install states that the plugin's hooks act in adopted repositories and that a
  consumer `permissions.deny` rule matching the same command blocks first, so the hook's
  message never reaches the agent.
- Supersedes the rejection of plugin hooks in archived change
  `2026-09-23-architect-review-length-and-bespoke-findings` (design, "keeps hooks out of the
  package").

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the plugin's component roots add `hooks`; the plugin ships the navigation hooks;
  plugin hooks act only in adopted repositories.

## Impact

- Added: `hooks/hooks.json`; `tests/publisher/test_navigation_policy.py` (moved from
  `tests/agent_process/`).
- Moved: `.agent-process/scripts/navigation_policy.py` → `skills/agent-process/scripts/navigation_policy.py`
  (gains the `pre-bash`/`pre-read` adapters and a `main`).
- Edited: `.agent-process/scripts/hooks.py` (on-edit only), `.claude/settings.json`,
  `skills/agent-process/SKILL.md` (Install), `tests/publisher/test_plugin.py`,
  `tests/publisher/test_start_change.py`, `tests/publisher/test_hooks.py`,
  `tests/agent_process/test_doc_headers.py`.
- Removed: `tests/agent_process/test_navigation_policy.py` (moved).
- Consumers: after the release, sessions in adopted repositories get the denials; a consumer with
  its own copy wired in settings runs both until it removes it (ekolvah/kinozal_scraper#612).
- No ADR: the decision is a distribution mechanism recorded in `design.md` and the spec delta;
  ADR 0021's mention of `navigation_policy.py` is historical and stays.
