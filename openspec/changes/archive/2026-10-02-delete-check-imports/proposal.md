## Why

`check_imports` in `.agent-process/scripts/ci_check.py:336-353` is dead code (#326). It was never
in `CHECKS`: `git log --all --oneline -S'"imports": check_imports'` prints nothing, and
`python .agent-process/scripts/ci_check.py --list` prints `["lint", "module-size",
"test-imports", "secrets", "pytest", "pip-audit", "pip-audit-dev", "requirements"]`. It could not
run here either: `git ls-files .importlinter src` prints nothing, and no requirements file pins
`import-linter`. It was written for a consumer with a `src/` layout. The one import rule this
repository enforces — test modules do not import test modules — is tach's `test-imports`, which
rejected import-linter (`test-import-guard` design D1).

## What Changes

- Delete `check_imports` from `.agent-process/scripts/ci_check.py`.
- The comment of `_secrets_cmd` (line 223) keeps its reason ("unreliable-on-PATH on Windows") and
  drops the pointer to `check_imports`.
- The docstring of `check_test_imports` (line 143) stays: it names import-linter as a rejected
  tool, not the deleted function.

## Capabilities

### New Capabilities

### Modified Capabilities

None. No requirement names `check_imports`, and no check runs or stops running, so the change sets
`skip_specs: true`.

## Impact

- Edited: `.agent-process/scripts/ci_check.py` only.
- Not touched: `check_mypy`, also unregistered, which the pending change `ci-check-mypy` owns.
