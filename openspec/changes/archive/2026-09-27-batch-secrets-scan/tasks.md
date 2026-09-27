## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py batch-secrets-scan --planner Claude --implementer Claude` for tracking issue 231. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 In `tests/agent_process/test_ci_check.py` add `test_targets_beyond_one_command_line`: monkeypatch `ci_check._tracked_files` to 600 distinct 80-character paths (none matching `_CAPTURED_HTML_FIXTURES`) and `ci_check._run` to record each command and raise `SystemExit(1)` for the command holding the last path. Assert that `ci_check.check_secrets()` raises `SystemExit` with code 1, more than one command was recorded, `len(subprocess.list2cmdline(cmd)) <= 32767` for each, and the paths after the `_secrets_cmd` prefix of every command, concatenated, equal the 600 paths in order. Run `python skills/agent-process/scripts/check_red.py tests/agent_process/test_ci_check.py::test_targets_beyond_one_command_line`; verify it fails in the test body; commit as `test(ci): secrets targets exceed one command line`

## 2. Batching (design: batch by measured length, fail fast)

- [x] 2.1 In `.agent-process/scripts/ci_check.py` add `_CMDLINE_LIMIT = 32000` and a helper that packs targets in order into batches whose `subprocess.list2cmdline(_secrets_cmd(batch))` stays within it (a single over-long path gets a batch of its own); make `check_secrets` keep the empty-list refusal and call `_run(_secrets_cmd(batch))` per batch. Verify `python -m pytest tests/agent_process/test_ci_check.py -q` passes and `python .agent-process/scripts/ci_check.py --only secrets` passes on Windows; commit as `fix(ci): batch the secrets scan under the command-line limit`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that every check passes, `secrets` included

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py batch-secrets-scan`. Verify that it archives the delta into `openspec/specs/`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: batch-secrets-scan" --body-file <report>`. The report names tracking issue 231 as a plain reference (never `Closes`) and carries the scenario → test map
- [ ] 4.3 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Targets beyond one command line → `tests/agent_process/test_ci_check.py::test_targets_beyond_one_command_line`
