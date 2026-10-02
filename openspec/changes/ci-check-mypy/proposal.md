## Why

`check_mypy` exists in `.agent-process/scripts/ci_check.py` and `mypy` is pinned in the dev
requirements, but `CHECKS` has never held it, so neither pre-push nor CI checks types (#325).

Observed on `main` `8c4f84d`, mypy 1.20.2 over the 59 modules of `ci_check._find_modules()`:

- As configured today (no `[tool.mypy]`): `tests\agent_process\git_bash.py: error: Source file
  found twice under different module names: "git_bash" and "tests.agent_process.git_bash"` —
  `Found 5 errors in 5 files (errors prevented further checking)`.
- With `--explicit-package-bases`: no mapping error, `Found 32 errors in 17 files (checked 59
  source files)`. By code: `assignment` 8, `index` 4, `union-attr` 4, `no-redef` 4,
  `import-not-found` 3, `misc` 3, `arg-type` 2, `call-overload` 1, `import-untyped` 1,
  `list-item` 1, `return-value` 1. The `import-not-found`/`no-redef` pairs are the
  `except ModuleNotFoundError: from gh_io import …` fallback of three scripts; the
  `import-untyped` is `jsonschema` in `start_change.py`; two are in `gh_io.slurp_named_records`,
  which nothing calls (`git grep slurp_named_records` → its definition only).
- That run had `import-linter` installed outside the lockfiles. CI installs only the lockfiles,
  where `from importlinter import api` in the unregistered `check_imports` adds
  `ci_check.py:350: error: … "importlinter"  [import-not-found]` (architect review). This change
  therefore follows `delete-check-imports` (#326), which removes that code; on that base the
  lockfile-only set is the 32 above.

## What Changes

- `ci_check` registers `mypy`; CI gains the `mypy` job through `--list`.
- mypy maps modules by explicit package bases.
- The 32 reported errors are fixed in code; no module is excluded.
- `types-jsonschema` joins the dev requirements; the unused `slurp_named_records` is removed.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: `ci_check` type-checks its Python modules.

## Impact

- Edited: `pyproject.toml` (`[tool.mypy]`), `.agent-process/scripts/ci_check.py`,
  `.agent-process/requirements-dev.in`, `.agent-process/requirements-dev.txt`,
  `.agent-process/scripts/gh_io.py`, `.agent-process/scripts/release_pr.py`,
  `.agent-process/scripts/head_review.py`,
  `.agent-process/scripts/check_blocking_review_threads.py`,
  `skills/agent-process/scripts/memory_checkpoint.py`, `skills/agent-process/scripts/edit_lint.py`,
  `skills/agent-process/scripts/manual.py`, `skills/agent-process/scripts/onboarding.py`,
  `tests/agent_process/git_bash.py`, `tests/agent_process/test_ci_check.py`,
  `tests/publisher/delivery_fakes.py`, `tests/publisher/init_harness.py`,
  `tests/publisher/test_init_conflicts.py`, `tests/publisher/test_init_config.py`,
  `tests/publisher/test_init.py`, `tests/publisher/test_head_review.py`,
  `tests/publisher/test_activate_protection.py`.
- Added, removed: none. No doc edit: no document lists the check set, and the decisions live
  in `design.md`.
