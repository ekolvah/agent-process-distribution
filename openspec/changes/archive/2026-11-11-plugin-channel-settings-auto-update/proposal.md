## Why

The `manual plugin-channel` row asks the person to turn on auto-update for
`agent-process-marketplace` under `/plugin` → Marketplaces. It is the one UI step of the row
(`skills/agent-process/scripts/manual.py`). Tracking issue 487 asks whether a setting or a
CLI flag can do it instead. Observed on Claude Code 2.1.296: `"autoUpdate": true` on the
marketplace's entry in user settings turns it on, and no CLI flag does (`design.md`
decision 1).

`_plugin_channel` reads auto-update only from `~/.claude/plugins/known_marketplaces.json`.
Claude Code takes the settings entry first (loading.md, "Which marketplaces and plugins
auto-update"). So the check sees a settings write only after a session start copies it into
that file (decision 1). By that precedence, a settings `false` over a stale known `true` turns
auto-update off, and the check misses it.

## Standard approach

- <https://code.claude.com/docs/en/plugins/loading.md#which-marketplaces-and-plugins-auto-update>:
  the precedence of the auto-update decision.
- <https://code.claude.com/docs/en/plugins/host-marketplace.md#turn-on-auto-update> and
  <https://code.claude.com/docs/en/plugins/org.md#set-update-policy>: the documented ways to
  turn it on.

## What Changes

- The `plugin-channel` row names `claude plugin marketplace add`, `claude plugin install`, and
  then `"autoUpdate": true` on the marketplace's entry in `~/.claude/settings.json`. It names
  no `/plugin` step.
- `_plugin_channel` takes the user-settings entry's `autoUpdate` when that entry sets one, else
  the known-marketplace entry's.
- The README install block and the SKILL.md migration text name the same settings write.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the requirement "The marketplace follows the stable channel".

## Impact

- Edited: `skills/agent-process/scripts/manual.py`, `tests/publisher/test_init_remote.py`,
  `README.md`, `skills/agent-process/SKILL.md`, `openspec/specs/distribution/spec.md` (by
  the archive).
- Added: `openspec/changes/plugin-channel-settings-auto-update/`, archived in the PR.
- Removed: none.
- Consumers: a machine set through the UI stays done. The toggle also writes the user-settings
  entry (loading.md), and a missing key falls back to the known-marketplace entry.
