## Why

Step 4 of issue 107 (issue 114) was split on 2026-09-24. `v2-4a-review-protection` (PR 173) removed
the v1 review control plane. This change removes the v1 issue and state scripts, so that the
Project `Status` field is the only delivery state and no v1 script can be run in place of a
v2 step.

The v2 flow no longer calls any of them. On 2026-09-25, on `main` at `a04859a`, a search for
their names outside `openspec/changes/archive/` and the ADRs found only these references:

- the scripts themselves: `open_pr.py` imports `check_orphan_scope.py`, `update_pr_body.py`
  imports `open_pr.py`, and `set_issue_status.py` and `set_issue_priority.py` import
  `project_settings.py`;
- their tests, `tests/agent_process/test_issue_branch.py` and
  `tests/publisher/test_deferred_scope.py`;
- prose that describes them as v1: `agent-process.md` (delivery step 4, the `## Out of scope`
  paragraph, governance item 5), `AGENTS.md`, `.claude/rules/workflow.md`, the retired
  installation guide, the `set_status.py` docstring, and the `Branch creation moves the issue
  to In Progress` requirement of `openspec/specs/state/spec.md`. That requirement still names
  the `issue-N-<slug>` branch, while v2 creates the branch with `start_change`.

No workflow, hook or skill script calls them. `bootstrap_github_project.py` from the brief no
longer exists (removed with the Copier mirror in `v2-0b`).

## What Changes

- **BREAKING** (for a v1 `issue-*` delivery): delete `.agent-process/scripts/issue_branch.py`,
  `new_branch.py`, `open_pr.py`, `update_pr_body.py`, `check_orphan_scope.py`,
  `set_issue_status.py`, `set_issue_priority.py` and `project_settings.py`, together with
  their tests. The generated `## Deferred scope` PR-body export is deleted with `open_pr.py`.
- `state`: the `In Progress` requirement names the branch that `start_change` creates instead
  of `issue-N-<slug>`.
- Prose that names the deleted scripts either points to the v2 command or is removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `state`: modifies `Branch creation moves the issue to In Progress`, so that the branch is
  the linked branch `start_change` creates and a board failure names the steps left.

## Impact

- Removed: `.agent-process/scripts/issue_branch.py`, `.agent-process/scripts/new_branch.py`,
  `.agent-process/scripts/open_pr.py`, `.agent-process/scripts/update_pr_body.py`,
  `.agent-process/scripts/check_orphan_scope.py`, `.agent-process/scripts/set_issue_status.py`,
  `.agent-process/scripts/set_issue_priority.py`, `.agent-process/scripts/project_settings.py`,
  `tests/agent_process/test_issue_branch.py`, `tests/publisher/test_deferred_scope.py`.
- Edited: `skills/agent-process/scripts/set_status.py` (the docstring only),
  `.agent-process/docs/architecture/agent-process.md`, `AGENTS.md`,
  `.claude/rules/workflow.md`, ADR 0027 (one Observations bullet).
- Unchanged: `.agent-process/docs/architecture/agent-process-installation.md`, which is
  already marked retired and says that the scripts it names no longer exist. Issue 115
  deletes it. Also unchanged: `.github/pull_request_template.md` (its `Closes #` line and
  `## Agent record`), `agent_orchestrator.py`, `roles.yaml` and `copier-answers.yml`, all
  owned by issue 115.
- External: open PR 104 (`issue-101-bug-telemetry-marks-no`, last updated 2026-09-12) loses
  `update_pr_body.py`. Its checks do not call it (design D2).
