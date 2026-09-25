## Why

After every propose run and every apply run the person asks by hand to have the plan or the
delivered change explained in plain words for a solution review (#176). The step is the same
each time, and the procedure does not name it, so it happens only when asked.

Observed carrier capability: the Claude Code session that proposes this change lists an
`Artifact` tool that publishes an HTML page as a private claude.ai link; the issue records that
Codex has no such tool. The procedure therefore names the outcome — a plain-words explanation
linked or written in the final message — and lets the carrier choose the medium.

## What Changes

- `## Architect review` of `skills/agent-process/SKILL.md`: once the issue is `Planned`, the
  planner explains the plan in plain words — what changes, why, what the person decides — as
  a page linked in its final message, or in that message when the carrier cannot publish one.
- `## Delivery`: at the stop, the implementer explains the delivered change the same way and
  links it in its final message.

No script, check or validator is added: the explanation is judged by the person.

## Capabilities

### New Capabilities

### Modified Capabilities
- `planning`: the propose run ends with a plain-words explanation of the plan.
- `implementation`: the implementing run ends with a plain-words explanation of the delivered change.

## Impact

- Edited: `skills/agent-process/SKILL.md`, `tests/publisher/test_planning_workflow.py`.
- Added: none. Removed: none.
- `.claude/commands/opsx/*` and the OpenSpec skills stay generated and untouched: both carriers
  reach the step through the `tasks` rule's pointer to the shared skill.
