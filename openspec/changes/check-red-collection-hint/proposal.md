## Why

Issue #251. For new code the natural RED step is a test whose import target does not exist
yet; `check_red` refuses that run (exit 2) and neither its message nor SKILL.md Group 1 says
how to reach a judgeable RED. The planner of `add-greet-function`
(`ekolvah/agent-process-sandbox-2`, release 3.0.0) found the stub pattern only by a separate
probe.

Reproduction (pytest 9.0.3, Windows, this session): `tests/test_greet.py` starts with
`from sandbox.greet import greet`; `check_red`'s own command
`python -m pytest --tb=no --maxfail=0 -p no:stepwise -o cache_dir=… --junitxml=r.xml` gives

- on the node ids: `ERROR: found no collectors for …::test_greets_by_name`, `collected 0
  items / 1 error`, **rc=4**;
- on the file path: `Interrupted: 1 error during collection`, **rc=2**;
- in both cases the report holds `<testcase classname="" name="tests.test_greet"><error
  message="collection failure">ImportError while importing test module …`.

Root cause: an import error is raised while pytest collects the module, so no test of it
runs and pytest ends the run as incomplete (rc 2 or 4). `check_red` correctly gives no
verdict on an incomplete run, but its message stops at `pytest did not complete the run
(rc=N)`. The knowledge that closes it — a signature stub whose failure occurs in the test
body — exists only in this repository's `.claude/rules/testing.md`, which consumers do not
receive.

## What Changes

- `check_red`: the incomplete-run message gains one conditioned sentence — a test module
  that failed at collection because its import target does not exist yet reaches a
  judgeable RED through a stub of the target whose body raises `NotImplementedError`. The
  exit stays 2; the report is still never judged.
- SKILL.md is not changed (design D2).

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: adds the requirement that a collection failure names the way to RED.

## Impact

- Edited: `skills/agent-process/scripts/check_red.py`, `tests/publisher/test_check_red.py`.
- Added: `openspec/changes/check-red-collection-hint/` (archived into
  `openspec/specs/implementation/spec.md` on delivery).
- No ADR: the decisions (trigger, no SKILL.md sentence, stub) are local to this message and
  recorded in `design.md`.
