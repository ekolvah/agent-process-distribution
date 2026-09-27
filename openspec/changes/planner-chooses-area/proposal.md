## Why

Solution review of PR 220: the person does not want the propose run to stop and ask for the
area. The planner already knows the change it just planned, so it can pick the area from the
Project's `Area` options itself; the person moves an issue to another area on the board when
the pick is wrong.

## What Changes

- The propose run chooses the area from the Project's `Area` options by the content of the
  change and asks the person nothing; an issue created outside a change gets its area the same way.
- `create_tracking_issue.py <change>` without `--area` on a change with no issue still exits 2,
  and its message now lists the Project's `Area` options, so the planner reads them in the
  same call instead of a separate `gh` query.
- `SKILL.md` and `.claude/rules/workflow.md` say "choose", not "ask".

## Capabilities

### Modified Capabilities
- `state`: "Area is set at creation" becomes "Area is chosen at creation"; scenario "Area asked
  once" becomes "Area chosen by the planner".
- `planning`: "Architect review is the last step of the propose run" — the area is chosen, not asked.
- `implementation`: "Delivery steps are tasks of every change" — the area was chosen by the propose run.

## Impact

- Edited: `skills/agent-process/scripts/set_status.py`,
  `skills/agent-process/scripts/create_tracking_issue.py`, `skills/agent-process/SKILL.md`,
  `.claude/rules/workflow.md`, `tests/publisher/test_start_change.py`,
  `tests/publisher/test_planning_workflow.py`.
- Tracking issue: the same as the change it corrects (#219); lands in PR 220.
