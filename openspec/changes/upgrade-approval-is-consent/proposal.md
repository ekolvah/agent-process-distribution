## Why

An upgrade asks the person twice: "yes" after `init --dry-run` (SKILL.md Install step 3), then
the approval of the upgrade PR, which the `agent-process person approves` ruleset already
requires (ADR 0040 D2, D7). Once the agent has its own identity and the run writes nothing
outside that PR, the approval is the person's control point and the "yes" adds nothing. The
person decided: on an upgrade the PR approval is the consent.

Observed: PRs opened from a session carrying the bot's `GH_TOKEN` are the bot's —
`gh pr view 496 --json author,mergedBy` prints author `ekolvah-agent`, merged by `ekolvah`
(likewise #494). `init` runs `gh` through `steps.run` with `env=None`
(`skills/agent-process/scripts/steps.py:36`), so its PR inherits the same identity.

## What Changes

- SKILL.md Install step 3: after the dry-run, skip the question when the plan writes nothing
  outside the PR and prints no `manual agent-identity` row; step 4 then enables auto-merge on
  the PR, asks the person to approve it, and after the merge runs step 5 only on a
  `manual protection` row. Every other run asks once, as now.

## Capabilities

### New Capabilities
- none

### Modified Capabilities
- `distribution`: a new requirement, `An upgrade's PR approval is its consent`; `Install continues
  past the installation PR` runs steps 5–6 on that path only for a `manual protection` row.

## Impact

- Edited: `skills/agent-process/SKILL.md` (Install steps 3 and 4),
  `tests/publisher/test_planning_workflow.py`, `openspec/specs/distribution/spec.md` (by
  archive).
- Added, removed: none. No script changes; `commands/init.md` stays true (both runs remain).
- ADR: none new; ADR 0040 D2/D7 already make the person's approval the merge gate of a bot's PR.
