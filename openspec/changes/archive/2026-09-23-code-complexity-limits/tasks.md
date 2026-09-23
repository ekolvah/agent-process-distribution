## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py code-complexity-limits --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 161; verify it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 In `tests/agent_process/test_ci_check.py` add `TestComplexityLimits`: each test builds a temporary git repository holding a copy of the real `.agent-process/pyproject.toml`, one tracked module under `.agent-process/scripts/` and an existing `tests/agent_process/` (else ruff reports `E902`), `chdir`s there, calls the check directly, and reads the tool output with `capfd`. `test_function_over_complexity_limit_fails_lint` (a function with 11 branches → `check_lint()` raises `SystemExit`, output names the function and `C901`); `test_module_over_size_limit_fails_module_size` (1001 lines → `check_module_size()` raises `SystemExit`, output names the module; 1000 lines passes); `test_stale_baseline_fails_lint` (a simple function carrying `# noqa: C901 -- baseline: x` → `check_lint()` raises `SystemExit`, output names `RUF100`). Add a signature stub `check_module_size` in `ci_check.py` (not registered) so the failure is in the test body
- [x] 1.2 Run `python skills/agent-process/scripts/check_red.py` with the three node ids of 1.1; verify it exits 0 with each RED; commit as `test(implementation): RED for complexity and module-size limits`

## 2. Limits

- [x] 2.1 Add `pylint` to `.agent-process/requirements-dev.in` and regenerate `.agent-process/requirements-dev.txt` with pip-compile; implement `check_module_size` and register it as `module-size` after `lint` (design D3); add the pylint sections to both `pyproject.toml` files (design D2); verify `python -m pytest tests/agent_process/test_ci_check.py -q -k module_size` is green and `python .agent-process/scripts/ci_check.py --only requirements` passes
- [x] 2.2 Add `C901`, `PLR0911`, `PLR0912`, `PLR0913`, `PLR0915`, `RUF100` to `select` of both `pyproject.toml` files (design D1, D4); verify `python -m pytest tests/agent_process/test_ci_check.py -q -k "complexity or stale_baseline"` is green; commit Group 2 as `feat(implementation): complexity and module-size limits in ci_check`

## 3. Existing violations

- [x] 3.1 Split `tests/publisher/test_init.py` (harness to `tests/publisher/init_harness.py`, fixtures to `tests/publisher/conftest.py`) and `tests/publisher/test_delivery_scripts.py` (`_script`, `_Gh` to `tests/publisher/delivery_fakes.py`) per design D5, moving no test; verify `python .agent-process/scripts/ci_check.py --only module-size` passes and `python -m pytest tests/publisher --collect-only -q` lists the same node ids as on `origin/main`
- [x] 3.2 Put `# noqa: <codes> -- baseline: <reason>` on each function design D4 lists, one reason per function (e.g. "CLI entry point mirrors its flags"); verify `python .agent-process/scripts/ci_check.py --only lint` passes; commit Group 3 as `refactor: fit existing code to the complexity limits`

## 4. Decision record

- [x] 4.1 Write `.agent-process/docs/adr/0028-standard-linters-limit-code-complexity.md` (MADR, `status: "accepted"`): the decision of design D1–D4 and D6, the superseded "complexity-lint gate was rejected" paragraph of ADR 0016 named per design D7, "Native alternatives considered" (radon/xenon, flake8 plugins, a bespoke counter, reviewer prose), the baseline list, and the deletion condition (remove `module-size` and pylint if ruff ships a module-length rule; drop the gate if the baseline grows instead of shrinking); verify `python -m pytest tests/agent_process -q -k "adr or doc"` is green; commit as `docs(adr): standard linters limit code complexity`

## 5. Verify

- [x] 5.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify every change and spec passes
- [x] 5.2 Run `python .agent-process/scripts/ci_check.py` and verify it passes, including `==> module-size`; confirm `git diff --name-only origin/main` lists only the paths of the proposal's Impact and the change directory

## 6. Deliver

- [x] 6.1 With a clean worktree run `python skills/agent-process/scripts/archive_change.py code-complexity-limits`; verify it applies the `implementation` delta, commits the archive, and pushes the branch
- [ ] 6.2 Run `gh pr create --title "code-complexity-limits" --body-file <report>`; the report references issue 161 without `Closes`, carries the scenario → test map and the baseline list, and states that `module-size` runs in CI from the first PR after merge (design, Risks)
- [ ] 6.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`; after each corrective push run both again; resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`, answer P2/P3 without resolving, run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- `implementation / Function over the complexity limit` → `tests/agent_process/test_ci_check.py::TestComplexityLimits::test_function_over_complexity_limit_fails_lint`
- `implementation / Module over the size limit` → `tests/agent_process/test_ci_check.py::TestComplexityLimits::test_module_over_size_limit_fails_module_size`
- `implementation / Stale baseline entry` → `tests/agent_process/test_ci_check.py::TestComplexityLimits::test_stale_baseline_fails_lint`
