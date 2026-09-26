## Context

`ci_check.py` already bounds module size with pylint (ADR 0028); the rule that test modules
do not import each other has no tool (#194). Candidate observations are in proposal.md — Why. A bespoke `ast` test was rejected earlier
(#193, design D5). v2 installs no publisher file into a consumer (ADR 0028, Scope), so the
check binds this repository only.

## Goals / Non-Goals

**Non-Goals:**
- Imports by `conftest.py` or helper modules: the glob declares `test_*` modules only, and
  both observed incidents were test → test.
- The unregistered `check_imports` (import-linter) and `check_mypy` in `ci_check.py` stay as
  they are.

## Decisions

**D1 — tach.** It is the only candidate that expresses "no `test_*` module imports a
`test_*` module" without listing modules. Rejected: import-linter (wildcards replace a whole
module segment only), ruff `TID251` (exact names; a pattern key is accepted and never
matches), bespoke `ast` test (#193, design D5).

**D2 — configuration in the root `pyproject.toml`.**
```toml
[tool.tach]
source_roots = ["."]

[[tool.tach.modules]]
path = "tests.**.test_*"
depends_on = []
```
One module declaration covers `tests/agent_process` and `tests/publisher`; modules outside
the glob (helpers) are not tach modules, so importing them is not reported (observed). No new
file.

**D3 — `test-imports` check.** Registered in `CHECKS` after `module-size`; runs
`[sys.executable, "-m", "tach", "check"]` through `_run`, the module form every other step
uses. tach's `[FAIL] <file>:<line>: … Module '<importer>' cannot depend on '<imported>'` line
names both modules.

**D4 — dependency.** `tach` in `.agent-process/requirements-dev.in`, the lock regenerated
with `pip-compile`; `pip-audit-dev` audits it and its transitive requirements (`gitpython`,
`networkx`, `prompt-toolkit`, `pydot`, `pyyaml`, `rich`, `tomli`, `tomli-w`). tach 0.35.1 has
no telemetry or usage-logging code (no match for `telemetry|anonymous|usage log` in the
package); its remote features (`--web`, `tach init` upload) are commands `ci_check` does not
run.

## Risks / Trade-offs

- [tach installs a `pytest11` plugin that loads whenever `[tool.tach]` exists] → without its
  `--tach*` flags it skips nothing, but it still runs impact analysis: the RED run of this
  change printed `[Tach] WARNING: 1 test(s) failed that would be skipped by impact analysis!`
  (a passing scratch run had printed nothing). Both `pyproject.toml` files therefore set
  `addopts = ["-p", "no:tach"]`; `check_red.py` reads the same `addopts`.
- [A new test module named outside `test_*`] → not a test to pytest either
  (`python_files = ["test_*.py"]`), so the glob matches what pytest collects.
- [tach's transitive dependencies join the dev environment] → dev-only, audited by
  `pip-audit-dev`, the same trade ADR 0028 accepted for pylint.

## Migration Plan

Main passes once the earlier test moves are in (#193): `python -m tach check` on this branch
printed `[OK] All modules validated!`. Rollback is reverting the PR.
