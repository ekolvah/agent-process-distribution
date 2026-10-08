## 0. Delivery start

- [x] 0.1 Run `agent-process start_change plugin-env-locks-rebuild --planner Claude --implementer Claude` for tracking issue 368. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/plugin-env-locks-rebuild`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py`, add a helper that loads `skills/agent-process/scripts/plugin_env.py` in-process under a module name of its own and sets its `MANIFEST` to `tmp_path / "requirements.txt"` (`# none\n`). It also replaces `_run` with a wrapper that records each command under the calling thread's name and then calls the real `_run` (D3). Then add:
  - `test_parallel_install_waits_and_reuses_the_environment` ("Scenario: Parallel install"). Thread A runs `install(data)`. At A's first `pip install`, the wrapper starts thread B running `install(data)` and waits up to 5 s for B's first command, then continues. Join both threads. Assert that B's commands are exactly one `pip check`, issued after A's last command; that B returns A's interpreter; and that `pyvenv.cfg` has the `st_mtime_ns` it had when A returned (D1).
  - `test_install_reports_a_lock_held_too_long` ("Scenario: Install waits too long"). Read `getattr(module, "LOCK_WAIT", None)`, then set `LOCK_WAIT` to 1 with `monkeypatch.setattr(..., raising=False)`. Thread A runs `install(data)`. At A's first `pip install`, the wrapper sets a `reached` event and then waits up to 10 s for a `release` event. The main thread waits up to 5 s for `reached` and calls `install(data)`. Assert that it raises `InstallError` naming `.lock` and `1 s`, and that it ran no command. Last, assert that the value read first is 240. In a `finally`, set `release` and join A (D2).
- [x] 1.2 Run `agent-process check_red tests/publisher/test_plugin.py::test_parallel_install_waits_and_reuses_the_environment tests/publisher/test_plugin.py::test_install_reports_a_lock_held_too_long`. Verify that it prints `RED: 2 failed` and exits 0. In the first test, B runs `venv --clear` while A installs (proposal Why, row 3). In the second, `install` builds instead of raising. Commit as `test(plugin): parallel installs clear the same environment`

## 2. Install under a lock

- [x] 2.1 In `skills/agent-process/scripts/plugin_env.py`, add `LOCK_WAIT = 240` and `_locked(path)` (D1, D2). It opens `path` in `a+b` mode and polls every second until `LOCK_WAIT` passes: `fcntl.flock(LOCK_EX | LOCK_NB)` on POSIX, `msvcrt.locking(LK_NBLCK, 1)` on Windows. It retries only on the observed lock-held errors, `PermissionError` on Windows and `BlockingIOError` on POSIX, and lets any other `OSError` propagate. On timeout it raises `InstallError(f"another session held {path} for {LOCK_WAIT} s")`. On exit it unlocks (`LK_UNLCK` at offset 0 on Windows) and closes. Extract `_usable(venv) -> bool` (`.complete` exists and `pip check` passes). Rewrite `install`: return when `_usable`. Otherwise run `data.mkdir(parents=True, exist_ok=True)`, enter `_locked(data / ".lock")`, return when `_usable` holds now, and otherwise build in place as today. Rewrite the module docstring sentence on parallel sessions to name the lock and the bounded wait. Verify that `python -m pytest tests/publisher/test_plugin.py -q -k "session_start or install"` passes. Commit as `fix(plugin_env): install the plugin environment under an exclusive lock`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change plugin-env-locks-rebuild`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: plugin-env-locks-rebuild" --body-file <report>`. The report references tracking issue #368 plainly, never with `Closes`. It carries the scenario → test map and the residuals from design Risks: the accepted rebuild of an environment another session uses after a failed `pip check`, and a start delayed by up to 240 s behind a slow install. It notes that the issue's second scenario is accepted, not fixed, and why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / First session → `tests/publisher/test_plugin.py::test_session_start_installs_the_plugin_environment`
- `distribution` / Manifest unchanged → `tests/publisher/test_plugin.py::test_session_start_installs_the_plugin_environment`
- `distribution` / Install fails → `tests/publisher/test_plugin.py::test_session_start_reports_a_missing_environment`
- `distribution` / Broken environment → `tests/publisher/test_plugin.py::test_session_start_installs_the_plugin_environment`
- `distribution` / Hook variables absent → `tests/publisher/test_plugin.py::test_session_start_reports_a_missing_environment`
- `distribution` / Manifest changed → `tests/publisher/test_plugin.py::test_session_start_keeps_the_previous_environment`
- `distribution` / Parallel install → `tests/publisher/test_plugin.py::test_parallel_install_waits_and_reuses_the_environment`
- `distribution` / Install waits too long → `tests/publisher/test_plugin.py::test_install_reports_a_lock_held_too_long`, `tests/publisher/test_plugin.py::test_session_start_reports_a_missing_environment` (an `InstallError` becomes the marker)
- `distribution` / Launcher uses the session interpreter → `tests/publisher/test_plugin.py::test_launcher_runs_the_session_interpreter`
