## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py test-import-guard --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 194. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `tach` to `.agent-process/requirements-dev.in`, regenerate `.agent-process/requirements-dev.txt` with `pip-compile`, install it, and add `[tool.tach]` to `pyproject.toml` (design: D2, D4). Verify `python -m tach check` prints `[OK] All modules validated!` on the branch
- [x] 1.2 `tests/agent_process/test_ci_check.py`: add `TestTestImports::test_test_module_importing_test_module_fails`. It builds a git repository in `tmp_path` with the `[tool.tach]` table read from the root `pyproject.toml`, `tests/publisher/test_a.py`, `test_b.py` importing `tests.publisher.test_a`, `helper.py`, and `test_c.py` importing only `tests.publisher.helper`; `ci_check.run_selected("test-imports")` raises `SystemExit`, and the output names `tests.publisher.test_b` and `tests.publisher.test_a` and not `test_c` — one call proves the registry name, the run path and the behaviour. Add a `check_test_imports` stub that returns, registered as `test-imports` in `CHECKS` after `module-size`, so the failure lands in the test body
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py tests/agent_process/test_ci_check.py::TestTestImports::test_test_module_importing_test_module_fails`, verify RED, commit as `test(implementation): ci_check forbids test-to-test imports (RED)`

## 2. Check

- [x] 2.1 `ci_check.py`: `check_test_imports` runs `[sys.executable, "-m", "tach", "check"]` through `_run` (design: D3). Verify `python -m pytest tests/agent_process/test_ci_check.py -q` is green (including `test_full_runner_visits_every_registered_check`), commit as `feat(implementation): ci_check forbids test-to-test imports`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes, `test-imports` included. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py test-import-guard`. Verify that it applies the `implementation` delta, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "test-import-guard" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`), carries the scenario → test map, and names the accepted gap (imports by `conftest.py` and helper modules stay unchecked)
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation / Test module imports a test module` → `tests/agent_process/test_ci_check.py::TestTestImports::test_test_module_importing_test_module_fails`
