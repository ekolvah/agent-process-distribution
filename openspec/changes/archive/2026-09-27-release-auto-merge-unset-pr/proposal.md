## Why

The `Release Please` run is red on every push to `main` that neither opens nor updates the
release PR, including the merge of each release PR; the open release PR stays without auto-merge (#208).

Observation, run 36297738914 (`38582bb`, re-run attempt): the action logged
`✔ PR https://github.com/ekolvah/agent-process-distribution/pull/208 remained the same`, then
the step `Enable auto-merge on the release PR` failed with
`The template is not valid. .github/workflows/release-please.yml (Line: 32, Col: 15): Error
reading JToken from JsonReader. Path '', line 0, position 0.`

Root cause: release-please-action filters out an unchanged PR, so `prs_created` is `false`
and the `pr` output is unset. Line 32 is the step's `env` entry
`PR: ${{ fromJSON(steps.release.outputs.pr).number }}`; the runner evaluated it although the
step's `if: steps.release.outputs.prs_created == 'true'` was false, and `fromJSON('')` failed
the step. Reproduction: `test_release_workflow_enables_auto_merge` currently asserts that
exact `fromJSON` entry, so it pins the defect.

## What Changes

- The auto-merge step of `.github/workflows/release-please.yml` passes the raw output
  (`PR_JSON: ${{ steps.release.outputs.pr }}`) and reads the number inside `run` with
  `jq -er .number`, which fails on a missing number; no step expression parses an output that may be unset.
- A run that opens or updates no release PR is green, the step skipped. A run that does still
  enables auto-merge, and a failure to enable it still fails the run.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: requirement "Releases go through release-please" gains that a run opening
  or updating no release PR succeeds.

## Impact

- Edited: `.github/workflows/release-please.yml`,
  `tests/publisher/test_reusable_workflows.py`, `openspec/specs/distribution/spec.md` (by the
  archive).
- Added: none. Removed: none.
- Docs: ADR 0031 D4 names the step and its `prs_created` guard, not the expression; it stays
  true and is not edited.
