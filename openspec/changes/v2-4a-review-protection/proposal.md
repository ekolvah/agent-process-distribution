## Why

This change removes the v1 review control plane, step 4 of the v2 plan
([#107](https://github.com/ekolvah/agent-process-distribution/issues/107),
[issue 114](https://github.com/ekolvah/agent-process-distribution/issues/114)). It was split into two changes during planning on
2026-09-24: this one covers review and protection, and `v2-4b` covers the v1 issue and state
scripts. The v2 review loop already exists: `v2-2b` made the `agent-review` check the review,
and `wait_for_pr.py` is its wait. Four v1 mechanisms still run beside it:

- `review_gate.py` judges a head from the classic and ruleset context lists and writes
  `.review_gate_stamp`. The v2 Deliver rule still names it as the last step.
- The Stop hook (`hooks.py stop`, `codex_hooks.py stop`, `delivery_state.py`) blocks a turn on
  that stamp, but only on a branch that matches `issue-N-<slug>`. On 2026-09-24,
  `python -c "…from new_branch import is_valid_branch_name as v; print(v('review-bespoke-standard'),
  v('v2-2j-remove-v1-quality-caller'), v('issue-101-bug-telemetry-marks-no'))"` printed
  `False False True`. Every v2 branch is named after its change by `gh issue develop --name
  <change>` (`start_change.py`), so the gate allows every v2 turn without reading anything.
- Classic branch protection is the only thing that requires `agent-review / agent-review`.
  On 2026-09-24, `gh api repos/ekolvah/agent-process-distribution/branches/main/protection`
  returned `contexts ["agent-review / agent-review"]`, `strict true`, `enforce_admins true`.
  Ruleset `23732345` ("agent-process default branch", active) requires only `agent-process /
  quality`. `install_branch_protection.py` writes classic protection, and the pre-push hook
  runs `check_branch_protection.py`, which compares it with a declared list before `ci_check`.
- `request_codex_review.py --request` posts `@codex review`, and so does `gh pr comment <PR>
  --body "@codex review"`.

The conditions and open questions of issue 114 are already settled, and are cited in
`design.md` (Context).

## What Changes

- **BREAKING** (for this repository's own gate): `review_gate.py` is deleted, together with
  `.review_gate_stamp` and the `## Agent record` verdict line in the PR template. After each
  push the Deliver rule runs `wait_for_pr.py` alone.
- **BREAKING**: The Stop turn gate is deleted: `delivery_state.py`, the `stop` subcommand of
  `hooks.py` and `codex_hooks.py`, and the `Stop` entries in `.claude/settings.json` and
  `.codex/hooks.json`.
- `activate_protection.py` also requires `agent-review / agent-review` when the default branch
  carries `.github/workflows/agent-review.yml`. The same preflight applies: the context needs a
  successful GitHub Actions run on the PR head, and it is bound to that app's integration ID.
  The read-back checks the exact list of contexts.
- `check_branch_protection.py` and `install_branch_protection.py` are deleted. The pre-push
  hook runs `ci_check` alone.
- `request_codex_review.py` loses `--request`, and the Deliver rule posts `gh pr comment <PR>
  --body "@codex review"`. Its `--wait` mode stays as the review check's reader.
- After the PR's head is green and before merge, the person runs `activate_protection --confirm`
  and deletes classic protection of `main` (design, Migration Plan). The process never writes
  classic protection.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review-and-merge`: removes `Required checks protect the default branch`, whose drift and
  review-gate scenarios go with their scripts. Adds `No local hook reads protection`.
- `implementation`: modifies `ci_check is the one command every gate runs`, whose push runs no
  protection probe, and removes `Stop hook names the next command`.
- `distribution`: modifies `Protection activation observes quality first`, which adds the
  review context when its caller is present, and `Activation reads back what it wrote`, which
  checks each context and no other, in any order.

## Impact

- Removed: `.agent-process/scripts/review_gate.py`, `.agent-process/scripts/delivery_state.py`,
  `.agent-process/scripts/check_branch_protection.py`,
  `.agent-process/scripts/install_branch_protection.py`,
  `tests/agent_process/test_review_gate.py`, `tests/publisher/test_delivery_state.py`,
  `tests/agent_process/test_branch_protection.py`.
- Added: `tests/agent_process/test_pre_push_hook.py`, which receives `TestPrePushHook` without
  its protection-probe tests.
- Edited scripts: `skills/agent-process/scripts/activate_protection.py` and
  `skills/agent-process/templates/ruleset.json` (its one-context placeholder),
  `.agent-process/scripts/request_codex_review.py` (removes `--request`),
  `.agent-process/scripts/hooks.py` and `.agent-process/scripts/codex_hooks.py` (remove `stop`),
  `.agent-process/scripts/gh_io.py` (a docstring that names `review_gate.py`),
  `.agent-process/.githooks/pre-push`.
- Edited configuration: `.claude/settings.json` and `.codex/hooks.json` (remove the `Stop`
  entries), `.gitignore` (removes `.review_gate_stamp` and `.agent_stop_blocks`),
  `.github/pull_request_template.md` (removes the review-gate verdict line).
- Edited tests: `tests/publisher/test_activate_protection.py`, `tests/publisher/test_hooks.py`,
  `tests/publisher/test_codex_hooks.py`, `tests/publisher/test_request_codex_review.py`,
  `tests/publisher/test_reusable_workflows.py` (its `REQUIRED_CONTEXTS` pin),
  `tests/publisher/test_planning_workflow.py` (the Deliver-rule order),
  `tests/agent_process/test_delivery_gate_wiring.py` (Stop wiring),
  `tests/agent_process/test_codex_project_trust.py` (a docstring that names the Stop gate).
- Docs: `skills/agent-process/SKILL.md` (Delivery, Install step 5),
  `.agent-process/docs/architecture/agent-process.md` (review loop, terminal state,
  Review-gate verdicts), `.agent-process/docs/architecture/agent-process-installation.md` (the
  classic-protection install step), ADR 0027 (one Observations bullet),
  `openspec/specs/implementation/spec.md` (the Purpose names the Stop gate).
- Left to issue 115: `agent_orchestrator.py`, `.agents/orchestration/roles.yaml`,
  `.agent-process/copier-answers.yml`. The only edit is the `contract` anchors of the `fixer` and
  `human_merge` roles in `roles.yaml`, which pointed at the deleted `#review-gate-verdicts`. Left to `v2-4b`: `issue_branch.py`, `new_branch.py`,
  `open_pr.py`, `update_pr_body.py`, `set_issue_status.py`, `set_issue_priority.py`,
  `project_settings.py`.
- External systems: the ruleset of this repository gains `agent-review / agent-review`, and the
  person deletes classic protection of `main`.
