## Context

See proposal.md — Why. The source modules are already grouped: `test_delivery_scripts.py`
by the script each test loads (`check_red` 64–170, `set_status` 172–250, `start_change` and
`create_tracking_issue` 253–692, `wait_for_pr` 693–878, `archive_change` 901–969), and
`test_init.py` mostly by `# --- …` section comments (467, 696, 883). `sandbox` and the module-scoped
`process_repo` come from `tests/publisher/conftest.py`, so every new `test_init_*` module gets
them without imports.

## Goals / Non-Goals

**Goals:** every module under `tests/publisher` is at most 700 lines (headroom under the
1000 limit; the largest after the move, `test_start_change.py`, is about 560), and no test module
imports from another test module.

**Non-Goals:** rewriting, renaming, or deduplicating any test or helper; splitting any other
module; changing the lint limit.

## Decisions

- **D1 — Delivery tests by script.** `test_check_red.py` (with `_fake_pytest` and the
  `subprocess.run`-boundary paragraph of the old docstring), `test_set_status.py`,
  `test_start_change.py` (`test_moved_start_scripts_resolve_consumer_root` with
  `MOVED_SCRIPTS`, lines 253–692, and both tests of `test_release_drift.py` with its private
  helpers), `test_pr_delivery.py` (lines 693–969, including `test_none_capture_is_an_error`,
  which spans `set_status`, `wait_for_pr`, and `archive_change`; two of its three rows are
  PR-delivery scripts). `_change`, `_CHANGE`, `_START`, `_GROUP0` stay beside their only
  users in `test_start_change.py`. Alternative from the issue: move them to
  `delivery_fakes.py` and keep `test_release_drift.py`; rejected because `_change` drags
  `_review` and `_CLASSES` along, and once the drift tests sit with the other
  `start_change` tests nothing is shared (§VII). `test_start_change.py` is about 560 lines.
- **D2 — `test_init.py` by its section comments.** The issue suggests grouping by installer
  step; the existing sections already are that grouping and keep each helper beside its
  users. `test_init.py` keeps the fixture-tag test, lifecycle, interruption/retry, and
  rendering/arguments (~330 lines); `test_init_config.py` takes lines 270–466
  (rerender, release line, consumer bytes, hooks — the tail of the `interruption and retry`
  section, which has no comment of its own; the line range defines it); `test_init_conflicts.py` 467–695;
  `test_init_remote.py` 696–882 (footprint, remote writes, Project phase — `_gh_kind` is
  used only there). Names used by more than one new module — `LABELS`, `CONSUMER_FILES`,
  `MARKETPLACE`, `PLUGIN`, `CHECK_COMMAND`, `CHECK_GROUP`, `_installed` — move to
  `init_harness.py` unchanged, and its docstring names the `test_init*` modules.
- **D3 — `openspec_cli.py`.** `OPENSPEC` and `_openspec` move to a new helper module that both
  `test_openspec_valid.py` and `test_planning_workflow.py` import; neither existing helper
  (`delivery_fakes`, `init_harness`) is about the OpenSpec CLI. `ROOT` stays in
  `test_openspec_valid.py` only if still used there.
- **D4 — Docstrings follow their tests.** Each new module's docstring carries the source
  paragraphs about the tests it takes (e.g. the `test_installed_footprint_is_closed` sentence
  of `test_init.py` goes to `test_init_remote.py`); a source keeps only what stays.
- **D5 — No permanent import guard here.** The issue's criterion is met once, by the move,
  and task 3.2 checks it. A guard that keeps it true is a separate change with its own
  issue (#194): a standard tool (import-linter's `forbidden` contract, or an alternative chosen
  there) is a new dev dependency and a `ci_check.py` step, and whether it takes a
  `tests.*.test_*` pattern is not yet observed. Rejected: a bespoke `ast` test under
  `tests/agent_process/` (a hand-written check where a standard tool exists); ruff
  `TID251` (bans modules by exact name, no pattern).
- **D6 — Proof of a pure move.** The collected ids, with the module path stripped, are the
  same multiset before and after: `python -m pytest tests/publisher --collect-only -q`
  piped through `sed 's/^.*:://' | sort` is saved in Group 1 and diffed in Verify, alongside
  `384 tests collected`. Moved text is compared with `git diff --color-moved` in review.

## Risks / Trade-offs

- [A test is dropped or duplicated in the move] → the D6 diff in task 3.2 on the
  implementer's head, and the pytest run of `ci_check.py` in the pre-push hook and CI.
- [A test depended on module state shared with a test now in another module] → the full
  `tests/publisher` run of `ci_check.py`.
- [The module-scoped `process_repo` is built once per `test_init*` module instead of once] →
  accepted: its setup is not among the three slowest steps of `test_init.py` (slowest call
  1.51 s at #3, 165 tests in 32.1 s), so four builds add seconds, not minutes.
- [A new test module imports another before the guard lands] → review only until the
  separate guard change; accepted.

Rollback is a revert of the PR; nothing outside `tests/` changes.
