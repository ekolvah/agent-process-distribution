## Why

A change planned from an existing issue got a second tracking issue (#242). Observed
2026-09-28: the propose run for #199 ended with `create_tracking_issue.py
releases-through-auto-update --area Distribution` on a `tasks.md` that still carried
`tracking issue <N>`; the script took its create branch and opened #241, a duplicate, while #199
stayed in `Todo` (fixed by hand: token set to `199`, the tail re-run, #241 closed).

Root cause: the procedure never tells the planner where an existing issue's number goes.
`SKILL.md` Group 0 says only that "the propose tail replaces the placeholder", so the planner
always writes `<N>`; the tail's existing-issue branch ("otherwise run it without area") works
only when the token already carries the number, and nothing asks the planner to write it.
`create_tracking_issue.py` behaves as its spec says: given a placeholder and `--area`, it
cannot know the change came from an issue.

## What Changes

- `SKILL.md` Group 0: the token carries the number of the issue the change is planned from,
  or the placeholder `<N>`, which the propose tail replaces.
- `planning` gains the requirement that a change planned from an issue is tracked by that
  issue.
- `.claude/rules/workflow.md`: "the propose run creates the tracking issue" becomes
  "creates it when the change has none".

## Capabilities

### New Capabilities

### Modified Capabilities
- `planning`: a change planned from an existing issue carries its number in Group 0, so the
  tail creates no second issue (ADDED).

## Impact

- Edited: `skills/agent-process/SKILL.md` (Group 0), `.claude/rules/workflow.md` (one
  sentence), `tests/publisher/test_planning_workflow.py` (new test),
  `openspec/specs/planning/spec.md` (by archive).
- Added: none. Removed: none. Scripts unchanged.
- No ADR: ADR 0027 (the `tracking issue <N>` token carries the number to both scripts)
  stands; this change names who writes the number when the issue already exists.
