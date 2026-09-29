## 0. Delivery start

- [x] 0.1 Run `agent-process start_change git-bash-in-tests --planner Claude --implementer Claude` for tracking issue 88. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/git-bash-in-tests`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `tests/agent_process/git_bash.py` with the signature stub `git_bash() -> str` that keeps today's selection (`shutil.which("bash")` plus the existing "bash unavailable" assertion). Add `tests/agent_process/test_git_bash.py::test_launcher_first_on_path_is_not_selected`: skipped with a reason off Windows or when `%SystemRoot%\System32\bash.exe` is absent. Otherwise it `monkeypatch`es `PATH` to `%SystemRoot%\System32` + `os.pathsep` + the current `PATH`, runs `[git_bash(), "-c", 'echo "$OSTYPE"']` with `capture_output=True, encoding="utf-8"`, and asserts exit 0 and stdout `msys` or `cygwin` (a WSL distribution would print `linux-gnu`)
- [x] 1.2 Run `agent-process check_red tests/agent_process/test_git_bash.py::test_launcher_first_on_path_is_not_selected` and verify that it fails in its body (the WSL launcher exits 1). Commit as `test: tests pick the WSL launcher as bash on Windows`

## 2. Fix

- [x] 2.1 `tests/agent_process/git_bash.py` (D1, D2): on `os.name == "nt"`, return `Path(<git --exec-path>).parents[2] / "usr" / "bin" / "bash.exe"`, captured with `encoding="utf-8"` and `check=True`. Assert that the file exists, naming the path, with no PATH fallback. Otherwise return `shutil.which("bash")` with the existing assertion. Replace the body of `TestPrePushHook._bash` in `tests/agent_process/test_pre_push_hook.py` and the `shutil.which` in `_run_guard` of `tests/publisher/test_reusable_workflows.py` with `git_bash()` (D3), and drop `shutil` imports that are no longer used. `TestPrePushHook._run` puts the directory of `_bash()` first on the hook's PATH, as Git does (D1, found in implementation). In `test_missing_interpreter_fails_loudly`, set PATH to the directory of `shutil.which("git")`, and assert `pre-push: no supported Python interpreter found` in stderr (D1 consumer). Verify that `python -m pytest -c .agent-process/pyproject.toml tests/agent_process -q` and `python -m pytest tests/publisher/test_reusable_workflows.py -q` pass
- [x] 2.2 Reproduce the issue's environment: run `powershell.exe -NoProfile -Command '$env:PATH=[Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User"); python -m pytest tests/agent_process/test_pre_push_hook.py tests/agent_process/test_git_bash.py tests/publisher/test_reusable_workflows.py -q -p no:cacheprovider'` and verify that everything passes with no skip (it was `8 failed` + `1 failed` before). Commit as `test: tests run Git's bash on Windows`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes and that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change git-bash-in-tests`. Verify that it commits the archive (no spec delta: `skip_specs`) and pushes the branch
- [ ] 4.2 Run `gh pr create --title "test: git-bash-in-tests" --body-file <report>`. The report references the tracking issue (#88) plainly, never with `Closes`. It carries the scenario → test map, the reproduction of proposal — Why, and the issue items left unchanged with the reason: the hook and push route already run Git's bash, and UTF-8 capture is already in place
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- n/a: `skip_specs`, so the change has no delta scenario. The defect is covered by `tests/agent_process/test_git_bash.py::test_launcher_first_on_path_is_not_selected` and by task 2.2's run of the existing hook and guard tests under the registry PATH.
