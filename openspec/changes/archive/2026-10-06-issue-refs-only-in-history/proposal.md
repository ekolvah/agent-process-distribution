## Why

Comments, docstrings and documents describe the current state; history lives in git, the
CHANGELOG, the ADR records and the OpenSpec archive. The rule lived in `project-map.md`,
deleted with the Copier mirror, and no check covers code. Observed on `main` at 9a9ebd0:
a scan of tracked files outside the ADR records, `CHANGELOG.md` and `openspec/changes/`
for `#N`, `issue N`, `PR N` and `pull request N` (wrapped lines included) finds 144
references in 40 files. PR 352 added `(issue 349)` to a workflow comment, a docstring and a
test, removed by hand. `tests/agent_process/test_doc_narrative.py` gates only the form of
`#N` in `.md` and allows a parenthetical `(#N)`, so the references accumulate.

Industry practice agrees: Google's developer documentation style guide (Timeless
documentation) keeps product and reference text to how it works now and reserves time-bound
text for release notes; ticket numbers and change history belong to version control.

## What Changes

- The rule is stated once, in the `maintenance` requirement "Documents are guarded".
- A `pre-commit` hook of the standard `pygrep` language enforces it: it fails a tracked text
  file outside the history records that carries an issue or PR reference. It runs at the
  `pre-commit` stage, so the edit-time lint shows the failure to the agent on the edit, and
  `ci_check lint` gates the head.
- `tests/agent_process/test_doc_narrative.py` is removed: once a reference is forbidden
  outside history, its form checks (parenthetical pointer, heading anchor, `workflow #N`) have
  nothing left to judge.
- The 144 existing references are removed, keeping each sentence about the current state;
  test fixtures that need a number build it from a constant. The pointers to the closed
  tracking issue (#107) in `CLAUDE.md` and `openspec/config.yaml` go with them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `maintenance`: requirement "Documents are guarded" — an issue reference is allowed only in
  history records, instead of only as a parenthetical pointer.

## Impact

- Added: `tests/agent_process/test_issue_refs.py`.
- Removed: `tests/agent_process/test_doc_narrative.py`.
- Edited (rule and hook): `.pre-commit-config.yaml`, `openspec/specs/maintenance/spec.md`
  (by archive).
- Edited (references removed): `CLAUDE.md`, `.agent-process/docs/telemetry-measurement-setup.md`,
  `.agent-process/scripts/ci_check.py`, `.agent-process/scripts/head_review.py`,
  `.github/workflows/agent-process.yml`, `.github/workflows/quality.yml`,
  `.github/workflows/release-please.yml`, `.github/workflows/reusable-agent-review.yml`,
  `openspec/config.yaml`, `pyproject.toml`, `skills/agent-process/SKILL.md`,
  `skills/agent-process/scripts/activate_protection.py`,
  `skills/agent-process/scripts/check_red.py`, `skills/agent-process/scripts/edit_lint.py`,
  `skills/agent-process/scripts/init.py`, `skills/agent-process/scripts/memory_checkpoint.py`,
  `skills/agent-process/scripts/onboarding.py`, `skills/agent-process/scripts/plugin_env.py`,
  `skills/agent-process/scripts/quality.py`, `skills/agent-process/scripts/start_change.py`,
  `skills/agent-process/scripts/wait_for_pr.py`,
  `skills/agent-process/templates/skill_check.py`, `tests/agent_process/git_bash.py`,
  `tests/agent_process/test_ci_check.py`, `tests/agent_process/test_delivery_gate_wiring.py`,
  `tests/agent_process/test_git_bash.py`, `tests/publisher/test_check_red.py`,
  `tests/publisher/test_head_review.py`, `tests/publisher/test_init.py`,
  `tests/publisher/test_init_config.py`, `tests/publisher/test_init_conflicts.py`,
  `tests/publisher/test_openspec_valid.py`, `tests/publisher/test_planning_workflow.py`,
  `tests/publisher/test_pr_delivery.py`, `tests/publisher/test_quality.py`,
  `tests/publisher/test_resolve_review_thread.py`,
  `tests/publisher/test_reusable_workflows.py`, `tests/publisher/test_set_status.py`,
  `tests/publisher/test_skill_check.py`, `tests/publisher/test_start_change.py`.
- No consumer-visible behaviour changes: the hook is this repository's own; the distributed
  scripts, templates and workflows change in comments and docstrings only.
