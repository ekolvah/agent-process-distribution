## 0. Delivery start

- [x] 0.1 Run `agent-process start_change hermetic-sandbox-push --planner Claude --implementer Claude` for tracking issue 278. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/hermetic-sandbox-push`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/init_harness.py` (D2, D4): `gitconfig(sb) -> str` renders the `[url "file:///no-network/"]` section with `insteadOf = https://`; `consumer_repo` writes its UTF-8 bytes (`write_bytes`: no CRLF translation on Windows) to `sb.home / ".gitconfig"` before the clone; `home_baseline(sb)` returns `{str(sb.home / ".gitconfig"): gitconfig(sb).encode()}`. In `tests/publisher/test_init.py`, `test_confirm_selects_release_before_composing` asserts `snapshot(sandbox.home) == home_baseline(sandbox)` and `test_init_takes_no_quality_command` asserts `snapshot(sandbox.root, sandbox.home) == home_baseline(sandbox)`; verify that both pass. Add `tests/publisher/test_init_remote.py::test_sandbox_push_runs_the_local_hook` beside the pre-push step tests (D3): `_installed(init, sandbox)`, assert `sandbox.home / "pre-push-ran"` is absent, write `# stale` into the config block as `test_update_keeps_consumer_bytes` does, assert `install(init, sandbox, "--confirm") == 0` with the captured output as message, then assert the record exists and `origin`'s installation branch is the clone's `HEAD`
- [x] 1.2 Run `agent-process check_red tests/publisher/test_init_remote.py::test_sandbox_push_runs_the_local_hook tests/publisher/test_init_config.py::test_update_keeps_consumer_bytes tests/publisher/test_init_config.py::test_consumer_session_start_is_not_owned` and verify that each fails in its body with `install` exiting 1 on the pre-commit clone of the guarded URL — #277's failure, now on `main`. Commit as `test: sandbox pushes reach the network through the pre-push hook`

## 2. Fix

- [ ] 2.1 D1 and D3: `gitconfig(sb)` adds the `[url "<sb.repo as posix>"]` section with `insteadOf = https://github.com/ekolvah/agent-process-distribution`; `tests/publisher/conftest.py::process_repo` writes the probe `.pre-commit-hooks.yaml` at the work tree's root before the `v{CURRENT}` commit. Verify that the three node ids of 1.2 pass
- [ ] 2.2 Run `python -m pytest tests/publisher -q` and verify that it passes with no new skip. Commit as `test: sandbox pushes resolve the hook repository locally`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes and that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change hermetic-sandbox-push`. Verify that it commits the archive (no spec delta: `skip_specs`) and pushes the branch
- [ ] 4.2 Run `gh pr create --title "test: hermetic-sandbox-push" --body-file <report>`. The report references the tracking issue (#278) plainly, never with `Closes`, and carries the scenario → test map and the reproduction of proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message; say that #277 needs a rebase by release-please after the merge to go green (the issue's last item). The person merges it

## Scenario → test map

- n/a: `skip_specs`, so the change has no delta scenario. The defect is covered by `tests/publisher/test_init_remote.py::test_sandbox_push_runs_the_local_hook` and by the five tests of `tests/publisher/test_init_config.py` that failed on #277, all red under the D2 guard before the fix.
