## Why

Install's Prepare (Install in `skills/agent-process/SKILL.md`) lists the person-only steps before the
first `init` — the `gh` logins and the review secret — but not the plugin channel. The person
meets it only as the `manual plugin-channel` row `init` prints after the installation PR opens
(`skills/agent-process/scripts/manual.py`, `_plugin_channel`), one more hand-off on the first
install (tracking issue 509). Step 4 of Install then lists that row among the post-PR actions.

## What Changes

- Prepare gains one bullet: once per machine, outside any project, `claude plugin marketplace add
  "ekolvah/agent-process-distribution#stable"`, `claude plugin install
  agent-process@agent-process-marketplace`, then `"autoUpdate": true` on that marketplace's entry
  in `~/.claude/settings.json`.
- Step 4 no longer names the `plugin-channel` row among the rows it tells the person to do.
- The plugin paragraph after the steps says the plugin is installed by Prepare, not by the row,
  and its release-tag migration points at Prepare's step instead of repeating the commands.
- `init` is unchanged: it already prints the row only while the channel is outstanding, so a
  machine that followed Prepare gets none.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec requirement covers Prepare or step 4's wording, and `init`'s output is
unchanged, so `skip_specs: true`.

## Standard approach

none found: this reorders the repository's own install prose. The README's Install section
already lists the same three commands as a once-per-machine prerequisite before
`/agent-process:init`.

## Impact

- Edited: `skills/agent-process/SKILL.md` (Install: Prepare, step 4, plugin paragraph).
- Edited (test): `tests/publisher/test_planning_workflow.py`
  (`test_install_names_the_skill_marker` asserts the commands in Prepare and no
  `plugin-channel` in step 4).
- Added, removed: none. No spec, ADR, README or script changes (design D2).
