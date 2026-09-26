## Why

A PR shows one line for quality, `agent-process / quality`. The driver behind it
(`ci_check.py`) runs nine checks — format, lint, module-size, test-imports, secrets,
pytest, pip-audit, pip-audit-dev, requirements — in one step and stops at the first failure.
So the merge box does not show what was checked, and a red `lint` hides whether `secrets` or
`pytest` pass. Observed on PR #202: the check list holds `agent-process / quality` as the
only quality entry.

## What Changes

- `quality.yml` takes an optional `checks` command that prints the check names as a JSON
  array. When it is given, each name runs `test --only <name>` in its own job, all of them
  independent. Without it, `test` runs once in one job, as today.
- The PR → issue link check becomes its own job.
- The job `quality` becomes a gate. It passes only when the link job, the check-listing job,
  and every check job succeeded, so the required context `agent-process / quality` and the
  ruleset stay unchanged.
- `ci_check.py --list` prints the `CHECKS` registry names as a JSON array, in run order.
- The publisher caller passes `checks: python .agent-process/scripts/ci_check.py --list`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the quality callee runs each listed check as its own job behind the gate
  `quality`; the quality driver runs each check once per PR.
- `implementation`: `ci_check` lists its checks.

## Impact

- Edited: `.github/workflows/quality.yml`, `.github/workflows/agent-process.yml`,
  `.agent-process/scripts/ci_check.py`, `tests/publisher/test_reusable_workflows.py`,
  `tests/agent_process/test_ci_check.py`.
- Not touched: `reusable-quality.yml` has no caller in this repository; only v1 consumers
  reach it at `@main` (design D6). The consumer template and `init.py` do not change:
  consumers keep one test job until they opt in (design D5). Ruleset, `activate_protection`,
  and the SKILL text do not change: the required context keeps its name.
- ADR: none. `design.md` records the alternatives. The decision reverses no earlier ADR.
- Cost: runner minutes grow with the number of checks (each job sets up Python and runs
  `setup`). Wall-clock time stays about the same because the jobs run in parallel.
