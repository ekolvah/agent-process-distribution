## Why

Parts 1 and 2 of the split of `v2-1-planning-workflow` (tracking issue #111) made the
OpenSpec propose/apply workflow an available route beside the v1 planner. Two planners in
one repository means two contracts to keep in step; the v1 one (per-label issue sections, a
`discovery` role, a fixture-capture script) is what v2 replaces. Part 3 removes it and makes
the docs say what the process is.

## What Changes

- **BREAKING** — the v1 planner entry points are removed: `/plan`, `/implement`, the
  `discovery` subagent, `$plan-issue`, `$implement-issue`, `change-classes.yaml`,
  `validate_issue_sections.py`, `capture_external_fixture.py`, `check_fixture_ratchet.py`
  and their tests. A consumer that still calls them takes the change through the
  `agent-process.md` planning section.
- `agent-process.md` describes planning as the OpenSpec workflow with the `agent-process`
  schema (tasks → architect review as the last artifact) and the delivery flow as the
  `tasks` rule; the roles table drops discovery and the runbooks; `principles.md`,
  `workflow.md` and `AGENTS.md` point at the new entry points.
- ADR 0009 (discovery as a role) is superseded by ADR 0027, whose observations record the
  three-part split and the review budget of the first apply.
- `test_adr_records.py` parses MADR sections with `markdown-it` instead of the removed
  `validate_issue_sections.find_gaps`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `planning`: no per-label artifact sets, no `discovery` role, no fixture-capture script
  (the requirement left out of part 2 because v1 still had them).

## Impact

- Removed: `commands/plan.md`, `commands/implement.md`, `agents/discovery.md`,
  `.agents/skills/plan-issue/`, `.agents/skills/implement-issue/`,
  `.agents/orchestration/change-classes.yaml`, `.agent-process/scripts/{validate_issue_sections,
  capture_external_fixture,check_fixture_ratchet}.py`,
  `tests/agent_process/test_validate_issue_status.py`.
- Edited: `.agent-process/docs/architecture/{agent-process,principles}.md`, ADR 0009, ADR 0027,
  `.claude/rules/workflow.md`, `AGENTS.md`, `.agents/orchestration/roles.yaml` (contract
  anchors only; the advisory control plane itself goes in `v2-4`),
  `tests/agent_process/test_adr_records.py`, `tests/publisher/test_planning_workflow.py`.
- Kept until `v2-4`/`v2-5`: `agent_orchestrator.py`, `roles.yaml`, `review_gate.py`,
  `open_pr.py`, `request_codex_review.py`, `verify_pr_link.py`.
