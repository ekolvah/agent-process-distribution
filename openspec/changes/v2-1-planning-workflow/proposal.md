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
- Scripts `wait_for_pr`, `set_status`, `check_red` (stdlib + `gh` only).
- **BREAKING**: `/plan #N`, the `discovery` role, `validate_issue_status` and the issue-form
  plan sections are replaced.

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
  `scripts/wait_for_pr.py`, `scripts/set_status.py`, `scripts/check_red.py`, `agents/architect-reviewer.md`.
- Removed: planner/implementer runbooks in `agent-process.md`, `discovery` subagent,
  `validate_issue_status.py`, `.agents/skills/plan-issue`, `.agents/skills/implement-issue`.
