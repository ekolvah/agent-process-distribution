## Why

A change of its own on the branch of PR 145 (`v2-2d-check-red-test`, issue 132), at
round 8 of its review, by the owner's decision: the fix changes a spec, so it goes through
a change (`tasks` rule of `openspec/config.yaml`).

Eight review rounds on a small diff came from two decisions of the archived D1, not from
eight defects:

- `--test "<runner command>"` was added for a future `init` input (issue 112) that has no
  consumer yet. An arbitrary string brought its own failure modes — a runner that does not
  start, a string that does not split, `--rootdir` in it, quotes on Windows — and each was
  a round (1, 2, 3). Principles §VII: an input without a consumer is paid for in review.
- The report is "what ran", and the run is shaped by configuration the script does not
  control. Every flag that cuts a run — `-x`, `--maxfail`, `--stepwise`, `--lf`/`--ff` —
  hides a green test behind a partial report, and the design recorded no boundary of what
  the gate guarantees. Rounds 5–8 each found the next flag; the count guard added at
  round 5 is dead for pytest once fail-fast is cancelled and misfires on a duplicate node
  id (round 8, P2).

Observations the design rests on (pytest 9.1.1, 2026-09-19, on record in the archived
`design.md` D1 of `v2-2d-check-red-test` and extended in this change's `design.md`): the
last `maxfail` on the command line wins over `-x` and over `addopts = -x`; `--stepwise`,
`--sw-skip`, `--lf`, `--ff` and `--nf` belong to the `cacheprovider` plugin and with
`-p no:cacheprovider` are "unrecognized arguments" (rc 4, no report written), while a plain
run under `-p no:cacheprovider` is unchanged (`1 failed, 1 passed`).

## What Changes

- `check_red.py`: `--test` is removed; the runner is `python -m pytest` of the script's own
  interpreter. The script runs it under its own configuration — `--tb=no --maxfail=0 -p
  no:cacheprovider --junitxml=<its own temporary file>` — and judges the report whole. The
  count guard (report short of the node ids → exit 2) is deleted. The boundary is recorded:
  an explicit selection in `addopts` (`-k`, `-m`, `--deselect`) is the project's
  configuration, and the gate judges the run under it.
- `openspec/config.yaml` `tasks` rule, Group 1: `check_red.py <node ids>` — no runner
  argument.
- `agent-process.md` step 3 and the ADR 0027 bullet of issue 132 follow.
- Tests: `test_behavioural_change` and `test_runner_owns_the_selection` drive the script
  through the `subprocess.run` boundary (§II); `test_partial_report_is_no_verdict` goes
  with the guard; `test_tasks_of_a_new_change` asserts the rule text.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `implementation`: "RED first for behavioural changes" — the runner is the script's own,
  the run is under the script's configuration; scenario "Runner given" now states that
  the runner is the script's own (its name stays: OpenSpec 1.13.0 refuses to drop a
  scenario from a MODIFIED block, design.md D1); scenario "Configuration that cuts the
  run" is added.

## Impact

Edited: `.agent-process/scripts/check_red.py`, `openspec/config.yaml`,
`.agent-process/docs/architecture/agent-process.md`,
`.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
`tests/publisher/test_delivery_scripts.py`, `tests/publisher/test_planning_workflow.py`,
`openspec/changes/archive/2026-09-19-v2-2d-check-red-test/design.md` (a pointer),
`openspec/specs/implementation/spec.md` (by the archive). Same PR (145).
