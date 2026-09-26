## Why

A test module that imports another test module appeared twice (`test_release_drift.py` ←
`test_delivery_scripts.py`, `test_planning_workflow.py` ← `test_openspec_valid.py`); #193
removed both by moving tests, but only review keeps the rule true (#194). Test code shares
helpers through non-test modules (`tests.publisher.delivery_fakes`, `init_harness`,
`openspec_cli`), which stay importable.

Observed on a scratch copy of `tests/` at `85bf807` plus
`tests/publisher/test_violation.py` (`from tests.publisher.test_set_status import PROJECT`),
per Principle V:

- **import-linter 2.15**, forbidden contract `forbidden_modules = tests.**.test_*` (and
  `tests.*.test_*`): `forbidden_modules: A wildcard can only replace a whole module.` — the
  rule cannot be written as a pattern.
- **ruff 0.15.12 `TID251`**: key `"tests.publisher.test_*"` → `All checks passed!` (silently
  never matches); key `"tests.publisher.test_set_status"` → `Found 1 error.` — exact names
  only, so every new test module would need its own entry.
- **tach 0.35.1**, `[tool.tach]` in `pyproject.toml` with one module `path = "tests.**.test_*"`,
  `depends_on = []`: `python -m tach check` → `[FAIL] tests\publisher\test_violation.py:1:
  … Module 'tests.publisher.test_violation' cannot depend on 'tests.publisher.test_set_status'`,
  exit 1; it also reports `import tests.publisher.test_init` and a function-local
  `from tests.agent_process.test_ci_check import x`. Without the violation:
  `[OK] All modules validated!`, exit 0. Helper imports are not reported.

## What Changes

- `ci_check.py` gains a `test-imports` check that runs `tach check`; it fails when a test
  module imports another test module and names both.
- `tach` joins the dev requirements.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: `ci_check` forbids a test module importing another test module.

## Impact

- Edited: `pyproject.toml` (`[tool.tach]`, `addopts`), `.agent-process/pyproject.toml`
  (`addopts`: design, Risks), `.agent-process/scripts/ci_check.py`,
  `.agent-process/requirements-dev.in`, `.agent-process/requirements-dev.txt`,
  `tests/agent_process/test_ci_check.py`.
- Added, removed: none. No doc edit: the rule, the alternatives and the observations live in
  `design.md`, as #194 allows.
