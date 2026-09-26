## Why

Observed on `main` at `340fa3f`: `tests/publisher/test_init.py` is 1000 lines, the
`max-module-lines` of `pyproject.toml` that `ci_check.py` enforces through pylint
`too-many-lines`, so the next test of `init.py` fails the lint step; `test_delivery_scripts.py`
is 969 (#193). Two test modules import from other test modules:
`test_release_drift.py` ← `test_delivery_scripts.py` (`_CHANGE`, `_GROUP0`, `_START`,
`_change`) and `test_planning_workflow.py` ← `test_openspec_valid.py` (`OPENSPEC`,
`_openspec`) — the second is not named in the issue but falls under its acceptance.
`python -m pytest tests/publisher --collect-only -q` → `384 tests collected`.

## What Changes

- Move only: no test body, assertion, parameter, or test name changes; helpers keep their
  names.
- `test_delivery_scripts.py` and `test_release_drift.py` are replaced by one module per
  script group: `test_check_red.py`, `test_set_status.py`, `test_start_change.py`
  (`start_change`, `create_tracking_issue`, the release-drift tests and the fixtures they
  share), `test_pr_delivery.py` (`wait_for_pr`, `archive_change`, the `None`-capture test).
- `test_init.py` keeps the lifecycle, retry, and rendering/arguments sections; the config
  and hooks section moves to `test_init_config.py`, the conflicts section to
  `test_init_conflicts.py`, the footprint, remote-write, and Project-phase sections to
  `test_init_remote.py`. Constants and `_installed`, used by several of them, move to
  `init_harness.py`.
- `OPENSPEC` and `_openspec` move to a new helper module `tests/publisher/openspec_cli.py`.
- No permanent guard against test-to-test imports: that is a separate change (design D5).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — test-module layout only; the change sets `skip_specs: true`.

## Impact

- Added: `tests/publisher/test_check_red.py`, `test_set_status.py`, `test_start_change.py`,
  `test_pr_delivery.py`, `test_init_config.py`, `test_init_conflicts.py`,
  `test_init_remote.py`, `openspec_cli.py`.
- Edited: `tests/publisher/test_init.py`, `init_harness.py`, `test_openspec_valid.py`,
  `test_planning_workflow.py`.
- Removed: `tests/publisher/test_delivery_scripts.py`, `test_release_drift.py`.
- Not edited: `delivery_fakes.py`; code under `skills/` and `.agent-process/`; archived
  changes' scenario → test maps and ADR 0028 (records of their time); no doc names the
  moved modules.
