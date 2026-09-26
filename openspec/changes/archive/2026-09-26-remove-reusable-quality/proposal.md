## Why

`.github/workflows/reusable-quality.yml` is the v1 quality callee. No workflow of this
repository calls it: `v2-2j-remove-v1-quality-caller` deleted its last caller, `ci.yml`, and
left the callee for v1 consumers pinned to `@main`, with its removal assigned to issue 115.
Issue 115 is closed, but the file stayed. The person confirms that no repository uses the
plugin, so the callee has no consumer. It still shows in the Actions sidebar, three tests
still pin its steps, and the planned change `quality-checks-per-job` (#204) would have to
reason around it (its D6).

## What Changes

- Delete `.github/workflows/reusable-quality.yml`.
- Tests: delete the two tests that exist only for that file
  (`test_quality_executes_a_trusted_driver_against_the_pr_worktree`,
  `test_quality_installs_product_dependencies_when_present`). Retarget the issue-link test to
  `quality.yml`. Drop the file from the callee list and from the
  `test_quality_runs_once_per_pr` filter. Add `test_the_v1_quality_callee_is_gone`.
- `quality.yml`: its link-step comment stops naming the deleted file.
- `.agent-process/copier-answers.yml`: drop the `workflow_references.quality` entry that
  points at the deleted file.

## Capabilities

### New Capabilities

### Modified Capabilities

None. No requirement of `openspec/specs/` names the file or its trusted-driver behaviour, so
the change sets `skip_specs: true`.

## Impact

- Removed: `.github/workflows/reusable-quality.yml`.
- Edited: `tests/publisher/test_reusable_workflows.py`, `.github/workflows/quality.yml` (one
  comment), `.agent-process/copier-answers.yml` (one entry).
- Not touched: `reusable-agent-review.yml`, which `agent-review.yml` still calls. ADR 0027 is
  history and stays as written. No ADR is needed: this carries out the removal that
  `v2-2j` and issue 115 already decided.
- `quality-checks-per-job` (#204) lands after this change. Its D6 and non-goal about this file
  then fall away, and `/opsx:update` reconciles them before its apply.
