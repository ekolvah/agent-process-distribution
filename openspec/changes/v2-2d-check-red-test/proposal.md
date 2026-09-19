## Why

Step 2d of the v2 plan (issue 107), tracked by issue 132; the first of three changes the
step was split into (2026-09-19, solution review: one change carried two rewritten and two
new scripts in one PR — the size that cost the review budget on issue 121). This change is
`check_red` alone; `wait_for_pr` is `v2-2e-wait-for-pr-checks`, the Group 0 scripts are
`v2-2f-start-change`.

`check_red --report <path>` reads a JUnit report at a path that `AGENTS.md` must declare and
`.gitignore` must hide: two conventions that exist only to feed the script. `pytest
--junitxml=<file>` writes the report wherever the caller says, so neither declaration is
needed when the script runs the runner itself.

Observation the design rests on: `python -m pytest --help` (pytest 9.1.1) prints
`--junit-xml=path      Create junit-xml style report file at given path`; `--junitxml` is
the alias the v1 branch of the script already passes.

## What Changes

- `check_red.py`: `--report` is removed; `--test "<runner command>"` (default
  `python -m pytest`) runs the runner with `--tb=no --junitxml=<temp file>` and the node
  ids, then evaluates the report as today.
- `AGENTS.md`: the test-runner declaration paragraph goes. `.gitignore`: the
  `.pytest-report.xml` entry goes.
- `openspec/config.yaml` `tasks` rule, Group 1: names `check_red.py --test "<runner>"`
  instead of "the runner declared in AGENTS.md, then `--report`".
- ADR 0027: the `check_red` row of "Native alternatives considered".
- Tests and the architecture page follow. `init` (issue 112) is out of scope; a future
  `test:` input of `init` would carry the same runner string.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `implementation`: "RED first for behavioural changes" (no `AGENTS.md` declaration; the
  runner command is `check_red`'s input).

## Impact

Edited: `.agent-process/scripts/check_red.py`, `openspec/config.yaml`, `AGENTS.md`,
`.gitignore`, `.agent-process/docs/architecture/agent-process.md`,
`.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
`tests/publisher/test_delivery_scripts.py`, `tests/publisher/test_planning_workflow.py`,
`openspec/specs/implementation/spec.md` (by the archive). Added: nothing. Removed: nothing.
One PR.
