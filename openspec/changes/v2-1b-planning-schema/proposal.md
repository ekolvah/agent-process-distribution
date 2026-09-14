## Why

v1 carries the planner runbook and the implementer runbook as bespoke prose duplicated per
agent adapter. OpenSpec ships the same propose → review → apply → archive loop as maintained
skills for both Claude Code and Codex; what the project adds is configuration.

Part 2 of 3 of the split of `v2-1-planning-workflow` (tracking issue #111): part 1
(`v2-1a-delivery-scripts`) added the scripts this change's `tasks` rule calls; part 3
(`v2-1c-remove-v1-planner`) removes the v1 entry points. This change is additive: v1 keeps
working beside it.

## What Changes

- The schema is forked to `openspec/schemas/agent-process/` with an `architect-review`
  artifact between `design` and `tasks`; `openspec/config.yaml` selects it.
- Project rules live in `config.yaml`: `proposal` (read first, ask, bug reproduction and
  root cause before design), `architect-review` (principles §I–VII, scenario coverage),
  `tasks` (the delivery tasks of every change: tracking issue with priority → linked branch
  → status → provenance line → RED first → … → `ci_check` → PR → `wait_for_pr` loop, three
  rounds → `finish_change`; a scenario → test map).
- `agents/architect-reviewer.md` writes the `architect-review` artifact from
  `openspec instructions`; no issue sections.
- `/opsx:propose` (`$openspec-propose`) becomes the planner and `/opsx:apply`
  (`$openspec-apply-change`) the implementer — as an available route; the v1 routes stay
  until part 3.

## Capabilities

### New Capabilities
- `roles`: which carrier fills each role in Claude Code and Codex; provenance; route
  selection.
- `planning`: how plans are produced, reviewed and approved.

### Modified Capabilities
- `implementation`: delivery steps are tasks of every change (the `tasks` rule).
- `state`: the delivery task that creates the tracking issue asks the person for the
  priority (moved here from part 1 with the rule).

## Impact

- Added: `openspec/schemas/agent-process/`, `config.yaml` `rules:`,
  `tests/publisher/test_planning_workflow.py`, this change's `architect-review.md`.
- Edited: `agents/architect-reviewer.md` (rewritten), `tests/publisher/test_openspec_valid.py`
  (`schema validate agent-process`), `openspec/config.yaml`.
- Removed: nothing; the v1 planner, its docs and ADRs go in part 3.
