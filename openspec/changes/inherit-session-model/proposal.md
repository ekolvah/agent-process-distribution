## Why

The plugin's only agent runs on a model nobody chose in the session. Observation: `agents/architect-reviewer.md:5-6` pins `model: claude-opus-5` and
`effort: high`, while the session that planned this change runs `claude-opus-5-5`. Root
cause: a frontmatter `model` outranks the main conversation's model, and a frontmatter
`effort` "Overrides the session effort level" (Claude Code sub-agents docs, `effort` row;
model order: "2. The subagent definition's `model` frontmatter, where `inherit` selects the
main conversation's model … 4. The main conversation's model", read 2026-10-03). A fixed id
goes stale with every model release and needs a manual bump; the process is interactive, so
the model and effort the person picked in the chat are the ones to use. Tracking issue #317.

## What Changes

- `agents/architect-reviewer.md` declares `model: inherit` and no `effort`, so the review runs
  on the session's model and effort.
- A test asserts that every plugin agent inherits both.
- Declined (#317's original ask): a model-pin policy or frontmatter check shipped for
  consumer agents.

## Capabilities

### New Capabilities

### Modified Capabilities
- `roles`: a plugin agent runs on the session's model and effort.

## Impact

- Edited: `agents/architect-reviewer.md`, `tests/publisher/test_plugin.py`.
- Spec: `openspec/specs/roles/spec.md` through the delta of this change.
- Added, removed: none. No doc names the pinned model.
