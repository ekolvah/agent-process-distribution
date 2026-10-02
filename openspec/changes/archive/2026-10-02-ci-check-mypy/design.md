## Context

See proposal.md — Why for the observations. `check_mypy` already runs
`python -m mypy <_find_modules()>` from the repository root, so mypy reads the root
`pyproject.toml`; only the registry entry and a configuration are missing. `tests/` has no
`__init__.py`, and test modules import helpers as `tests.agent_process.git_bash`, while mypy
derives a bare `git_bash` from the file path — the duplicate that stops it today.

## Goals / Non-Goals

**Goals:** mypy runs as a registered check over the full module set and passes on `main`.

**Non-Goals:** stricter flags (`strict`, `check_untyped_defs`, `warn_unused_ignores`) — a later
change once a defect they catch is observed. The unregistered `check_imports` is removed by
`delete-check-imports` (#326), which this change follows (proposal, Why).

## Decisions

- **D1 — Module mapping by `explicit_package_bases`.** `[tool.mypy]` in the root
  `pyproject.toml` sets `explicit_package_bases = true`: a file maps to its path from the
  repository root, the name the imports use. Observed: the flag alone removes the mapping error
  (proposal, Why). Alternatives: `__init__.py` under `tests/` changes the module names pytest
  imports by, in two configurations, for a type-checker setting; `mypy_path` with
  `.agent-process/scripts` makes `gh_io` reachable as both `gh_io` and `scripts.gh_io`, the same
  duplicate; excluding `tests/` drops half the module set.
- **D2 — The script-run import fallback keeps a scoped ignore.** `release_pr.py`,
  `head_review.py`, `check_blocking_review_threads.py` import `scripts.gh_io`, falling back to
  `gh_io` when run as a script from `.agent-process/`. mypy checks both branches, so the
  fallback line carries `# type: ignore[import-not-found, no-redef]`, scoped to those codes.
  Alternative: dropping the fallback changes how three workflow scripts are run, outside this
  issue.
- **D3 — `types-jsonschema` stubs.** The typeshed stubs join `requirements-dev.in`, as
  `types-PyYAML` did. Alternative: `ignore_missing_imports` for `jsonschema` would hide a
  wrong call on its API.
- **D4 — Remove `slurp_named_records`.** Nothing calls it; its two errors also mark a latent
  `AttributeError` (a non-object page reaches `.get` before the shape check). Deleting dead code
  is smaller than fixing and testing a path nothing runs.
- **D5 — Fix the remaining errors by annotation and narrowing.** Each is a too-narrow
  annotation, an untyped default, or a narrowing mypy cannot follow (`manual.py` guards
  `entry` through `channel`; the `reconfigure` calls on `sys.stderr`). Fixes keep runtime
  behaviour; the existing tests of those modules prove it. No module is excluded.
- **D6 — Registry position.** `mypy` follows `test-imports`: the static checks run before
  `secrets` and `pytest`. The `--list` matrix of `quality.yml` turns it into a job that the
  aggregate job already `needs`.

- **D7 — Plugin users get no mypy from this change.** `.agent-process/` and `ci_check.py`
  stay in this repository; the plugin ships `skills/agent-process/`, where no script names
  `ci_check` or `mypy`. A consumer's `quality` workflow runs the `test` its own
  `.github/agent-process-quality.json` declares (`distribution` spec, *The quality callee
  runs the declared commands*), and pre-push runs that same `test` through `agent-process-quality`. So a
  consumer type-checks only by declaring it: its `test` runs mypy (directly, or as one name of
  its `checks`), or its `.pre-commit-config.yaml` declares a mypy hook, which the plugin's
  edit-time lint then runs on each edited file and `pre-commit run --hook-stage pre-commit --all-files` in its `test`
  runs at the gate (SKILL.md, Install). What reaches them is the plugin scripts' type-only
  fixes (D5), with no behaviour change; the root `pyproject.toml`, which pre-commit installs
  for the `agent-process-quality` hook, gains a `[tool.mypy]` table that `pip install` ignores.
  Alternative: declaring mypy in the installer's template — rejected, the declaration belongs to
  the repository (issue 249, `quality.py`), and the template declares no linter. Shipping a
  quality toolchain to consumers revisits that decision (#328).

This adds no script: mypy is the standard type checker, already pinned.

## Risks / Trade-offs

- [A mypy bump reports new errors] → the version is pinned in `requirements-dev.txt`; a bump is
  its own PR whose `mypy` job shows them.
- [A new helper or script reintroduces a duplicate module name] → the `mypy` job fails with
  the mapping error on that PR, before merge.
- [A local environment holds packages the lockfiles do not] → a local `Success` can differ from
  CI; the PR's own `mypy` job, installed from the lockfiles only, is the proof.
- [Pre-push gets slower] → mypy's cache (`.mypy_cache/`, ignored) keeps reruns incremental.

## Migration Plan

Rollback: remove the `mypy` entry from `CHECKS`; the configuration and fixes stay harmless.
