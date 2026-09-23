---
status: "accepted"
date: 2026-09-23
decision-makers: ekolvah
---

# Standard linters limit code complexity

## Context and Problem Statement

Nothing in `ci_check.py` bounded the size of a function or a module. On `main` at `8a2552c`,
ruff reported 20 findings in 12 functions at its default complexity limits, and two test
modules had passed 1 000 lines (`tests/publisher/test_init.py` 1 216, `test_delivery_scripts.py`
1 011). `init.install`, where the installer grows, went from complexity 13 to 14 in #160.
The only guard was reviewer prose ([ADR 0016](0016-review-gate-blocks-on-narrow-simplicity-violations.md)),
which does not measure and does not stop growth (#161).

This record supersedes one paragraph of ADR 0016, the one that begins "A separate
complexity-lint gate was rejected as new dependency and gate surface". ADR 0016's chosen outcome,
its two reviewer triggers, stays in force, and ADR 0016 remains `accepted`.

## Considered Options

* ruff's complexity rules plus pylint's `too-many-lines`, both at their default limits
* radon/xenon
* flake8 plugins (`mccabe`, a module-length plugin)
* A line counter written into `ci_check.py`
* Reviewer prose only (the status quo of ADR 0016)

## Decision Outcome

Chosen: **the standard rules of the linters the repository already uses, at their documented
defaults.**

* Functions: ruff `C901` (complexity 10), `PLR0911` (returns 6), `PLR0912` (branches 12),
  `PLR0913` (arguments 5) and `PLR0915` (statements 50), selected in both `pyproject.toml`
  files. Preview-only rules (`PLR0914`, `PLR0917`, `PLR0904`) are left out, because a preview
  rule can change meaning between ruff releases.
* Modules: pylint `too-many-lines` (`C0302`, 1 000 lines), run by the `module-size` check of
  `ci_check.py` after `lint`. Each `pyproject.toml` disables every other pylint message, so the
  two linters never overlap.
* Baseline: an existing violation carries `# noqa: <codes> -- baseline: <reason>` on the
  function it excuses. `RUF100` fails the run once that function is back under the limits, so
  the suppression cannot outlive its cause. `per-file-ignores` was rejected because it would
  also exempt future functions, and a separate baseline file was rejected as a second place
  to keep in sync.
* Scope: this repository only. v2 installs no publisher file into a consumer, so the limits
  are not imposed on consumer product code.

The two oversized test modules were split by moving harness and fakes out, not tests. The
baseline at adoption is:

* `agent_orchestrator._decision`, `_planning_decision` and `_review_decision`, plus
  `delivery_state.decide`: v1 control-plane code that v2 removes
  ([ADR 0027](0027-v2-standards-replace-the-bespoke-control-plane.md)).
* `check_blocking_review_threads.review_threads` and `resolve_review_thread.review_threads`.
* `resolve_review_thread.close_round` and `request_codex_review.wait_for_review`.
* `init._checkout`.
* `init.install`, whose refactoring is tracked in #162.
* The test fakes `delivery_fakes.Gh.__call__` and `init_harness.install`.

### Native alternatives considered

* radon/xenon measure what ruff already measures, at the cost of a second tool.
* flake8 plugins bring a second linter framework, and no module-length plugin is a de-facto
  standard.
* A bespoke counter is exactly what "scripts over instructions" allows only when no standard
  tool exists. pylint has one.
* Reviewer prose (ADR 0016) grades a diff but cannot bound growth that happens one small PR
  at a time.

### Consequences

* Good, because a function or module that crosses a limit now fails CI, with the function
  or module named in the output.
* Good, because every exception is visible at its function and expires by itself (`RUF100`).
* Bad, because `pylint` and its `astroid` dependency join the dev requirements. They are
  dev-only and covered by `pip-audit-dev`.
* Bad, because `PLR0913` counts pytest fixtures as arguments. A test that needs more than five
  fixtures gets a baseline entry or a combined fixture.

### Deletion condition

Remove `module-size` and pylint if ruff ships a stable module-length rule. Drop the gate
altogether if the baseline grows instead of shrinking.

### Confirmation

`tests/agent_process/test_ci_check.py::TestComplexityLimits` proves the three scenarios of the
`implementation` spec: a function over the complexity limit fails `lint`, a module over
1 000 lines fails `module-size`, and a stale baseline entry fails `lint`.
