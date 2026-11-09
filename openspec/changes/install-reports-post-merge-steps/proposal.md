## Why

Installing 3.29.0 in a consumer (ekolvah/lampa-mediacenter#38) ended with its PR merged and
Install step 6, the agent's own GitHub identity, never run. The person learned of it from the
SessionStart marker `agent-process agent identity not set (the session has no GH_TOKEN) — fix:
agent-process agent_identity --bot <login> --dry-run`; following it alone left
`allow_auto_merge: false`, so `gh pr merge --auto` (ADR 0040 D7) fails.

Root cause, from the code:

- Steps 5 and 6, the steps after the installation PR merges, exist only as prose in
  `skills/agent-process/SKILL.md` Install. The deterministic end of install, the `manual` rows
  of `init` (`manual.rows`, `skills/agent-process/scripts/manual.py:83`), has no row for
  either, so neither a fresh install nor an upgrade prints that they are pending. A skipped
  step 5 is reported nowhere: no row, no session-start marker.
- `IDENTITY_FIX` (`skills/agent-process/templates/skill_check.py:42`) names only
  `agent_identity --dry-run`; `gh repo edit --enable-auto-merge` and the restart live only in
  SKILL.md.

## What Changes

- `init` prints a `manual protection` row while the default branch does not require both
  process checks, a `manual agent-identity` row while this clone holds no agent token, and a
  `manual auto-merge` row while the repository disallows auto-merge.
- The SessionStart identity marker's fix names the rest of step 6, auto-merge included; the
  `agent-identity` row carries the same fix text.
- SKILL.md Install step 4 names the new rows among those the person is told to do.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: three new requirements add the rows; `Manual rows follow observed state`
  gains the three states in its observed-done scenario; `A Claude session start reports a
  missing agent identity` names the full fix.

## Impact

- Edited: `skills/agent-process/scripts/manual.py`, `skills/agent-process/templates/skill_check.py`,
  `skills/agent-process/SKILL.md`, `tests/publisher/init_harness.py`,
  `tests/publisher/test_init_remote.py`, `tests/publisher/test_skill_check.py`,
  `openspec/specs/distribution/spec.md` (by archive).
- ADR 0040: does not apply; its D5 names the marker, not its fix text, and steps 5–6 are
  unchanged.
- Added, removed: none.
