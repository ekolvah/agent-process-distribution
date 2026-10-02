## 0. Delivery start

- [x] 0.1 Start once `delete-check-imports` (#326) is merged into `main` (`gh issue view 326` reads closed; proposal, Why). Run `agent-process start_change ci-check-mypy --planner Claude --implementer Claude` for tracking issue 325. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/ci-check-mypy`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [ ] 1.1 `tests/agent_process/test_ci_check.py`: add `TestMypy::test_type_error_fails_mypy`. It builds a git repository in `tmp_path` with a copy of the repository's own root `pyproject.toml` (as `TestComplexityLimits._process_repo` copies its configs), `tests/agent_process/helper.py`, `tests/agent_process/test_x.py` importing `tests.agent_process.helper`, and `.agent-process/scripts/subject.py` holding `x: int = "s"`; `ci_check.run_selected("mypy")` raises `SystemExit`, and the output read with `capfd` names `subject.py` and `[assignment]` and lacks `found twice` — one call proves the registry name, the mapping and the failure
- [ ] 1.2 Run `agent-process check_red tests/agent_process/test_ci_check.py::TestMypy::test_type_error_fails_mypy`. Verify that it fails in its body (unknown check `mypy`, no `[assignment]` in the output). Commit as `test(implementation): ci_check type-checks (RED)`

## 2. Configuration and registry

- [ ] 2.1 Root `pyproject.toml`: add `[tool.mypy]` with `explicit_package_bases = true` (design: D1). `ci_check.py`: register `"mypy": check_mypy` after `test-imports` (D6). Verify that test 1.1 passes and `python .agent-process/scripts/ci_check.py --only mypy` reports type errors and no `found twice`. Commit as `feat(implementation): ci_check type-checks`

## 3. Type errors

- [ ] 3.1 Add `# type: ignore[import-not-found, no-redef]` to the `from gh_io import …` fallback of `release_pr.py`, `head_review.py`, `check_blocking_review_threads.py` (D2). Verify that `ci_check.py --only mypy` no longer reports them
- [ ] 3.2 Add `types-jsonschema` to `.agent-process/requirements-dev.in`, regenerate `.agent-process/requirements-dev.txt` with `pip-compile`, install it (D3). Verify that `ci_check.py --only mypy` reports no `import-untyped` and `ci_check.py --only requirements` passes
- [ ] 3.3 Remove `slurp_named_records` from `.agent-process/scripts/gh_io.py` (D4). Verify that `git grep slurp_named_records` prints nothing
- [ ] 3.4 Fix the remaining errors by annotation and narrowing, without runtime change, in `memory_checkpoint.py`, `edit_lint.py`, `manual.py`, `onboarding.py`, `tests/agent_process/git_bash.py`, and the `tests/publisher` files of the proposal's Impact (D5). Verify that `ci_check.py --only mypy` prints `Success` and `ci_check.py --only pytest` passes; the PR's own `mypy` job (5.3), installed from the lockfiles only, is the CI proof (design, Risks). Commit as `fix(implementation): clear the type errors mypy reports`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes, `mypy` included; `--list` prints `mypy` after `test-imports`. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `agent-process archive_change ci-check-mypy`. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: ci-check-mypy" --body-file <report>`. The report references the tracking issue plainly (#325), never with `Closes`, and carries the scenario → test map and the Non-Goals of the design (stricter mypy flags), its base on #326, and D7 (how a plugin user runs mypy)
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation / Type error` → `tests/agent_process/test_ci_check.py::TestMypy::test_type_error_fails_mypy`
