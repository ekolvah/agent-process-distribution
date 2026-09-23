## Why

Nothing in this repository limits function complexity or module size: both ruff configs select
only `E, F, I, BLE, TRY400`, and [ADR 0016](../../../.agent-process/docs/adr/0016-review-gate-blocks-on-narrow-simplicity-violations.md)
rejected a complexity-lint gate. `tests/publisher/test_init.py` reached 1216 lines in PR #160
with no check reacting (issue #161).

Observed on `main` at `8a2552c`:

- `python -m ruff check --select C901,PLR0911,PLR0912,PLR0913,PLR0915` (ruff 0.15.12, default
  limits) reports 20 findings in 12 functions across both lint scopes.
- ruff has no module-length rule. `python -m pylint --rcfile <toml with disable=["all"],
  enable=["too-many-lines"], max-module-lines=1000> $(git ls-files '*.py')` (pylint 4.0.9)
  reports `C0302 Too many lines in module` for `tests/publisher/test_init.py` (1216/1000) and
  `tests/publisher/test_delivery_scripts.py` (1011/1000), exits 16, and takes 3.2 s.
- `ruff check --select PLR0913,RUF100` on `def f(...):  # noqa: PLR0913 -- baseline: <reason>`
  suppresses that finding and still reports an unsuppressed twin, so a reason after the codes
  is accepted.

## What Changes

- Both ruff configs select `C901`, `PLR0911`, `PLR0912`, `PLR0913`, `PLR0915` at their default
  limits, plus `RUF100` so a baseline entry that no longer suppresses anything fails lint.
- `ci_check.py` gains a `module-size` check: pylint `too-many-lines` at its default 1000 lines,
  configured in each scope's `pyproject.toml`. `pylint` is added to the dev requirements.
- The two oversized test modules are split below the limit; the 12 over-limit functions are
  baselined in place with `# noqa: <codes> -- baseline: <reason>`.
- ADR 0028 records the gate and supersedes ADR 0016's rejection of a complexity-lint gate.
- The limits stay repository-local: v2 consumers run their own quality command.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `implementation`: `ci_check` fails on a function over the complexity limits or a module over
  the size limit.

## Impact

Edited:

- `pyproject.toml`, `.agent-process/pyproject.toml` — rule selection and pylint config
- `.agent-process/scripts/ci_check.py` — `check_module_size` in `CHECKS`
- `.agent-process/requirements-dev.in`, `.agent-process/requirements-dev.txt` — `pylint`
- `tests/agent_process/test_ci_check.py` — tests of both limits
- baseline comments: `.agent-process/scripts/agent_orchestrator.py`,
  `.agent-process/scripts/check_blocking_review_threads.py`,
  `.agent-process/scripts/delivery_state.py`, `.agent-process/scripts/request_codex_review.py`,
  `skills/agent-process/scripts/init.py`, `skills/agent-process/scripts/resolve_review_thread.py`
- `tests/publisher/test_init.py`, `tests/publisher/test_delivery_scripts.py` — split

Added:

- `tests/publisher/conftest.py`, `tests/publisher/init_harness.py`,
  `tests/publisher/delivery_fakes.py` — moved harness and fakes
- `.agent-process/docs/adr/0028-standard-linters-limit-code-complexity.md`

Removed: none.
