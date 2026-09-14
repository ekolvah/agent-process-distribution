## Why

v1 carries the planner runbook, a discovery role, an issue-section validator and the
implementer runbook as bespoke prose duplicated per agent adapter. OpenSpec ships the same
propose → review → apply → archive loop as maintained skills for both Claude Code and Codex.

## What Changes

- `/opsx:propose` (`$openspec-propose`) is the planner; the plan is an OpenSpec change.
- Project rules (RED first, bug reproduction, scenario → test mapping, ask priority) live in
  `openspec/config.yaml`; the schema is forked to add an `architect-review` artifact.
- The GitHub steps (tracking issue, linked branch, `In progress`, `check_red`, `ci_check`,
  PR, `wait_for_pr`, archive) are tasks that the `tasks` rule puts into every `tasks.md`, so
  the unmodified `openspec-apply-change` runs them; no wrapper skill.
- Scripts `wait_for_pr`, `set_status`, `finish_change` (stdlib + `gh` + `openspec` only);
  `check_red` gains `--report <junit.xml>` and keeps its v1 CLI.
- **BREAKING**: `/plan #N`, `/implement #N`, the `discovery` role, `validate_issue_sections`,
  the fixture-capture scripts and the issue-form plan sections are replaced.

## Capabilities

### New Capabilities
- `roles`: which carrier fills each role in Claude Code and Codex.
- `planning`: how plans are produced, reviewed and approved.
- `implementation`: here RED first, branch linking, end of the implementing run; the rest
  arrives with `v2-2-delivery` and `v2-4-review-and-state`.
- `state`: here priority at creation; the rest arrives with `v2-4-review-and-state`.

### Modified Capabilities
<!-- none -->

## Impact

- Added: `openspec/schemas/agent-process/`, `openspec/config.yaml` rules,
  `.agent-process/scripts/{wait_for_pr,set_status,finish_change}.py`,
  `openspec/changes/v2-1-planning-workflow/architect-review.md`,
  `tests/publisher/test_planning_workflow.py`.
- Edited: `.agent-process/scripts/check_red.py` (`--report`), `agents/architect-reviewer.md`
  (rewritten: writes the artifact, no issue sections), `tests/agent_process/test_adr_records.py`
  (own `## ` section parser instead of the removed validator's `find_gaps`),
  `tests/publisher/test_openspec_valid.py` (`schema validate agent-process`), `AGENTS.md`,
  `.claude/rules/workflow.md`, `.agent-process/docs/architecture/{agent-process,principles}.md`,
  ADR 0009 (superseded by ADR 0027), ADR 0027 (observations from v2-1).
- Removed: `commands/plan.md`, `commands/implement.md`, `agents/discovery.md`,
  `.agents/skills/plan-issue/`, `.agents/skills/implement-issue/`,
  `.agents/orchestration/change-classes.yaml`,
  `.agent-process/scripts/{validate_issue_sections,capture_external_fixture,check_fixture_ratchet}.py`,
  `tests/agent_process/test_validate_issue_status.py`; in `agent-process.md` §Discovery runbook,
  §Planner runbook, §Architect review contract, the evidence-capture table and the
  planner/implementer steps of §Deterministic delivery flow.
- Kept until v2-4/v2-5: `set_issue_status.py`, `set_issue_priority.py`, `request_codex_review.py`,
  `open_pr.py`, `agent_orchestrator.py`, `roles.yaml` (its dangling `contract:` anchors
  included), the delivery hooks.
- Root-only: the Copier mirror is gone (`v2-0b`, #119), so no `.jinja` twin or allowlist row
  accompanies any removal above.
- Tracking issue: the v1 issue body stays the tracker contract until this change archives (#111).
