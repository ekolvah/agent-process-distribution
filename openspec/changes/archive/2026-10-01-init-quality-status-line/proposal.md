## Why

After a confirmed `agent-process init` (3.2.2) the installing agent relayed the
`manual quality-command` row to the person as something to do, "quality-command пока делать
не нужно…", and the person could not tell what it asked (#290). It asks nothing: the row
reports a state, that CI runs no tests until a change declares `test`.

Root cause: `_manual` (`skills/agent-process/scripts/init.py:778-790`) prepends that state
line to the `manual` rows and gives it the `manual` prefix, while `init`, Install step 4 of
`skills/agent-process/SKILL.md` ("Tell the person to do those rows") and the agent's relay
all treat `manual` rows as the person's outstanding actions. The spec fixes the same shape:
`Init asks for no quality command` requires a `manual quality-command` row, and the scenario
`Observed done` expects it among the `manual` rows. Reproduction: the current
`tests/publisher/test_init.py::test_quality_command_marker` asserts exactly that row.

## What Changes

- `init` prints the missing test declaration as a status line `quality: <declaration> declares
  no test -- CI runs no tests until the change that adds the first tests declares
  {"test": "<command>"}`, before the `manual` rows; the `manual` rows carry only actions.
- Install step 4 of `SKILL.md` no longer mentions the `quality-command` row; the module
  docstring of `init.py` names the status line instead of a row.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: `Init asks for no quality command` prints a `quality:` status line instead of
  a `manual quality-command` row; `Manual rows follow observed state` expects no `manual` row at
  all when every state is observed done.

## Impact

- Edited: `skills/agent-process/scripts/init.py`, `skills/agent-process/SKILL.md`,
  `tests/publisher/test_init.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/test_planning_workflow.py`.
- Added: `openspec/changes/init-quality-status-line/` (archived into
  `openspec/specs/distribution/spec.md` on delivery).
- No ADR: the decision (status line, not a row) is local to `init`'s output and recorded in
  `design.md`.
