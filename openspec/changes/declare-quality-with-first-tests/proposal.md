## Why

Issue #249. `init` requires `--test` at install time, before the consumer has any tests, so the
operator has to invent a placeholder, and nothing ever asks for it to be replaced.

**Observation (2026-09-28, `ekolvah/agent-process-sandbox-2`, release 3.0.0).**
`gh api repos/ekolvah/agent-process-sandbox-2/contents/.github/workflows/agent-process.yml`
shows the managed caller passing `test: "python -c \"pass\""`. PR #4 (`feat: add-greet-function`)
added `tests/test_greet.py`, and `agent-process / quality` stayed green without running it: its
only proof was local, through `check_red` at RED and a manual `python -m pytest` in Verify. A
regression after the merge would not turn CI red.

**Root cause.** The quality command is asked for at the wrong moment. At install it may not
exist yet. Under RED-first, the first change that alters behaviour brings the first tests, and
that is the moment the runner is known. `init` forces a value at install (`required=True`,
`init.py` `_parser`). That value is then fixed in a file the consumer must not edit ("rerun it
instead of editing this file"), and neither `init`, CI nor `check_red` marks a quality command
that tests nothing. Any exit-0 command is indistinguishable from a real run by its exit code, so
the fix removes the forced placeholder instead of trying to detect it.

## What Changes

- **BREAKING** `init` no longer takes `--test` or `--setup`. The managed caller passes no input
  to `quality.yml`, and the config block no longer names a quality command.
- The quality commands move to a consumer-owned declaration, `.github/agent-process-quality.json`
  (`{"setup": …, "test": …, "checks": …}`, with `test` required). The change that brings the
  first tests adds it in its own PR, so that PR already proves its tests in CI.
- `quality.yml` reads the declaration from the PR's checkout. Without one it runs no test and
  shows a `::warning::` annotation saying the run tests nothing. A malformed declaration fails
  the check.
- `check_red` exits 2 without running pytest while the declaration declares no `test`. This is
  the hard stop: the first change with tests cannot pass RED without declaring the command.
- `init` prints a `manual quality-command` marker while no `test` is declared. On upgrade, an
  existing managed caller that passes a `test` input that no declaration holds is a `conflict`,
  so an upgrade never silently drops a consumer's running tests.
- The publisher dogfoods the same source: its caller passes no input, and its declaration
  holds today's `setup`, `test` and `checks`.
- SKILL: Install asks for no command; Verify runs the declared `test`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the quality callee runs the declared commands (renamed from the caller's
  commands); callers pass no input; init asks for no quality command and marks its absence.
- `implementation`: RED first — `check_red` refuses while no quality command is declared.

## Impact

Added:
- `skills/agent-process/scripts/quality.py` — reads and validates the declaration; the
  `--github-output` mode that `quality.yml` runs from the trusted checkout.
- `.github/agent-process-quality.json` — the publisher's declaration.
- `tests/publisher/test_quality.py` — the declaration reader and its CI outputs.

Edited:
- `skills/agent-process/scripts/init.py` — drops `--test`/`--setup`; renders the caller and config
  block without them; adds the marker row and the upgrade conflict.
- `skills/agent-process/templates/agent-process.yml`, `skills/agent-process/templates/config.yaml`.
- `skills/agent-process/scripts/check_red.py` — refusal before the run.
- `.github/workflows/quality.yml` — no inputs; the plan job reads the declaration.
- `.github/workflows/agent-process.yml` — no `with:`.
- `skills/agent-process/SKILL.md` — Install steps 1–2, Tasks group 1 and Verify.
- `openspec/config.yaml` — its context names the declaration instead of repeating the command.
- `tests/publisher/test_init.py`, `init_harness.py`, `test_init_config.py`, `test_init_conflicts.py`,
  `test_start_change.py`, `test_plugin.py`, `test_check_red.py`, `test_reusable_workflows.py`,
  `test_planning_workflow.py`.

Removed: none. No ADR: design.md records the decision and its alternatives, and no existing ADR
decides where the quality command lives.
