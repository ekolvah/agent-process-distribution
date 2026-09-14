## Why

Nothing in v1 guarantees that every acceptance criterion is tested: a reviewer may notice a
gap, or not. A deterministic mapping (scenario → named test → green run) is a check, not a
review comment.

## What Changes

- `check_coverage` runs in the reusable workflow as a required check: every scenario of the
  PR's change has a test that ran green, or `n/a: <reason>` in the approved `tasks.md`.
- A publisher test fails CI when a requirement in `openspec/specs/` has no test naming it.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `review-and-merge`: adds the coverage gate.
- `maintenance`: adds the requirement-level coverage rule for this repository.

## Impact

- Added: `scripts/check_coverage.py`, `tests/test_spec_coverage.py`.
- Reusable workflow gains one required check.
