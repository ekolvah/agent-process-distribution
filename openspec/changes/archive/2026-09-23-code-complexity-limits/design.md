## Context

See proposal.md — Why for the observations. `ci_check.py` lints two scopes: the process paths
(`.agent-process`, `tests/agent_process`) with `.agent-process/pyproject.toml`, and, when
`_has_product_scope()`, the rest of the checkout with the root `pyproject.toml`. CI runs the
driver from the default branch, but ruff and the tools it calls read the PR's configs and the
PR's dev requirements (`reusable-quality.yml` installs `pr/.agent-process/requirements-dev.txt`).

## Goals / Non-Goals

**Goals:** standard rules at standard limits, configured where each tool reads its config;
every current violation fixed or visibly baselined.

**Non-Goals:** refactoring the 12 baselined functions; limits for consumer product code;
changing ADR 0016's two reviewer triggers.

## Decisions

**D1 — ruff `C901`, `PLR0911`, `PLR0912`, `PLR0913`, `PLR0915` at default limits** (complexity 10,
returns 6, branches 12, arguments 5, statements 50), added to `select` of both configs. The
limits are ruff's (= pylint's) documented defaults, so no value needs a rationale of its own.
Preview-only rules (`PLR0914`, `PLR0917`, `PLR0904`) are left out: a preview rule can change
meaning between ruff releases. Rejected: radon/xenon — a second tool for what the linter in use
already measures.

**D2 — module size by pylint `too-many-lines` (`C0302`), default 1000.** ruff has no module-length
rule. Each `pyproject.toml` gets `[tool.pylint."messages control"] disable = ["all"]`,
`enable = ["too-many-lines"]` and `[tool.pylint.format] max-module-lines = 1000`, so pylint runs
as a single-rule checker and cannot overlap ruff. Rejected: a line counter in `ci_check.py`
(bespoke; the issue asks for a standard tool) and flake8 plugins (a second linter framework,
none of them a de-facto standard).

**D3 — `check_module_size` mirrors `check_lint`.** Registered as `module-size` after `lint`. It
runs `python -m pylint --rcfile .agent-process/pyproject.toml` on the `_find_modules()` files
under `_PROCESS_PATHS`, and, when `_has_product_scope()` and the root `pyproject.toml` has a
`[tool.pylint]` section, `python -m pylint --rcfile pyproject.toml` on the remaining files. An
empty product list skips that run, as `check_mypy` does. A product scope without that section
prints that it is not checked: without it pylint would run its full default rule set, and a
consumer would get limits it did not configure (D6). Any non-zero pylint exit (a bit mask; 16 = convention) fails through
`_run`. Explicit file lists, not directories: pylint needs no package layout and never imports
the files.

**D4 — baseline = inline `# noqa: <codes> -- baseline: <reason>`, kept honest by `RUF100`.**
The entry sits on the function it excuses, names its rules, and ruff reports it as unused once
the function is under the limits. Rejected: `per-file-ignores` (exempts whole files from the
rule, including future functions) and a separate baseline file (a second place to keep in sync).
Baselined: `agent_orchestrator.py` ×3, `check_blocking_review_threads.review_threads`,
`delivery_state.py` ×1, `request_codex_review.py` ×1, `init._checkout`, `init.install`,
`resolve_review_thread.review_threads`, `resolve_review_thread` ×1 (9 arguments), the
`_Gh.__call__` fake and `_install` test helper. The reason on `init.install` points to its
refactoring issue (#162).

**D5 — split the two test modules by moving shared scaffolding, not tests.** `test_init.py`
keeps every test; its harness classes and helpers (`Project`, `FakeGitHub`, `Sandbox`,
`Runner`, `_install`, …) move to `tests/publisher/init_harness.py` and its fixtures
(`process_repo`, `sandbox`) to `tests/publisher/conftest.py`. `test_delivery_scripts.py`
keeps every test; `_script` and the `_Gh` fake move to `tests/publisher/delivery_fakes.py`.
Moved names become public, since they are now imported. Test node ids stay unchanged; no
tracked file outside the archive names them (`git grep "test_init.py::"`). Fixtures go to
`conftest.py` because a fixture imported into a test module is shadowed by the parameter of
the same name (ruff `F811`).

**D6 — repository-local.** v2 installs no publisher file into a consumer (distribution spec,
"The installed footprint is closed"), and the consumer's quality command is its own (`--test`),
so the shared quality workflow does not impose these limits. A v1 render that still carries
`.agent-process/` gets the process-scope rules with process code that already passes them.

**D7 — ADR 0028 supersedes only ADR 0016's rejected option.** ADR 0016's chosen outcome (two
reviewer triggers) stands and ADRs are immutable, so 0016 keeps `status: accepted`; ADR 0028
names the superseded paragraph. ADR 0028 carries "Native alternatives considered" and a
deletion condition (maintenance spec).

## Risks / Trade-offs

- [This PR's CI runs `ci_check.py` from `main`, which has no `module-size` check] → the ruff
  rules do apply in this PR's CI (they come from its configs); `module-size` is proven on this
  head by the pre-push `ci_check` run (local driver) and by the test of task 2.1, and by CI from
  the first PR after merge.
- [`PLR0913` counts pytest fixtures as arguments] → a test needing more than five fixtures
  gets a baseline entry with its reason or a combined fixture; accepted as the standard's cost.
- [`pylint` pulls `astroid` and friends into dev requirements] → dev-only, pinned by
  pip-compile and covered by the existing `pip-audit-dev` check.

## Migration Plan

One PR. Rollback: revert it; no data or external state changes.
