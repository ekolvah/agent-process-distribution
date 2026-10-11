## 0. Delivery start

- [x] 0.1 Run `agent-process start_change session-task-attribution --planner Claude --implementer Claude` for tracking issue 395. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/session-task-attribution`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add to `tests/publisher/conftest.py` an autouse fixture that deletes `CLAUDE_CODE_SESSION_ID`. Tests run inside a Claude Code session, and without the fixture the existing script tests would bind that real session in the clone's ledger. Verify that `python -m pytest tests/publisher` still passes
- [x] 1.2 Write the tests of the scenario map below against a signature stub of `skills/agent-process/scripts/session_binding.py` (`bind(issue, *, environ, ledger)` and `sessions(issue, *, ledger)`, design D2). In `tests/publisher/test_session_binding.py`, also write:
  - `test_same_issue_binds_once` (D2): a second `bind` of the same issue leaves one ledger line
  - `test_side_issue_refused_before_create` (D3): `create_tracking_issue` of a change without a number, in a session bound to another issue, exits 2 and makes no `gh issue create` call
  - `test_rerun_after_failed_archive` (D4): after an `openspec archive` failure, a second `archive_change` passes the clean-worktree check and rewrites `sessions`

  `test_second_task_in_one_session` also asserts that `gh issue develop` is not called and that the message names both issues. `test_task_pr_merged` asserts the exact header of the spec's column list, and that the Loki and Prometheus queries carry `session_id=~` and no `task_id`. Run `agent-process check_red` on these node ids and commit RED with the Group 1 ticks

## 2. Session binding (design D1–D4)

- [x] 2.1 Implement `session_binding.py` as in D2. Verify with `python -m pytest tests/publisher/test_session_binding.py`
- [x] 2.2 Call `bind` in `create_tracking_issue.py`, `start_change.py` and `archive_change.py` at the points of D3. Make `archive_change` write `openspec/changes/<change>/sessions` as in D4. Add `session_binding.py` to the `MOVED_SCRIPTS` sets of `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`. Verify with `python -m pytest tests/publisher`. Commit

## 3. Readings (design D5)

- [ ] 3.1 Change `.agent-process/scripts/task_readings.py` as in D5. Verify with `python -m pytest tests/agent_process/test_task_readings.py`. Commit

## 4. Docs (design D5, D6)

- [ ] 4.1 Add `.agent-process/docs/adr/0038-task-telemetry-follows-the-bound-sessions.md` (D1, D2, D5, D6), and point the status line of ADR 0037 to it
- [ ] 4.2 In `.agent-process/docs/telemetry-measurement-setup.md`, rewrite "Which labels carry the task", the columns of "Per-task readings" and "Per-task metrics" as in D5 and D6. Add the one-session-one-task rule and its message. Verify that `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py tests/agent_process/test_issue_refs.py` passes. Commit as `docs: task telemetry follows the bound sessions`

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits
- [ ] 5.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 5.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 6. Deliver

- [ ] 6.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change session-task-attribution`. Verify that the archived change holds a `sessions` file that lists this session's id, and that the script archives, commits and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: session-task-attribution" --body-file <report>`. The report references tracking issue #395 plainly, never with `Closes`. It carries the scenario → test map and the post-merge check of design, Migration
- [ ] 6.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change. The explanation gives the person the post-merge check:
  - read the PR's row with `git fetch origin task-readings && git show origin/task-readings:task-readings.csv`
  - verify that the header is the new column list, and that the row's `gap` names no telemetry cell
  - close tracking issue 395 once the row is seen

  The person merges it

## Scenario → test map

| Scenario (`measurement`) | Test |
|---|---|
| Task PR merged | `tests/agent_process/test_task_readings.py::test_task_pr_merged` |
| Re-run for a recorded PR | `tests/agent_process/test_task_readings.py::test_rerun_for_a_recorded_pr` |
| File with an earlier header | `tests/agent_process/test_task_readings.py::test_file_with_an_earlier_header` |
| Task without telemetry | `tests/agent_process/test_task_readings.py::test_task_without_telemetry` |
| Grafana unreachable | `tests/agent_process/test_task_readings.py::test_grafana_unreachable` |
| Parallel session of another task | `tests/agent_process/test_task_readings.py::test_parallel_session_of_another_task` |
| Second task in one session | `tests/publisher/test_session_binding.py::test_second_task_in_one_session` |
| Bound session without telemetry | `tests/agent_process/test_task_readings.py::test_bound_session_without_telemetry` |
| Plan creates the issue | `tests/publisher/test_session_binding.py::test_plan_creates_the_issue` |
| No session variable | `tests/publisher/test_session_binding.py::test_no_session_variable` |
| Plan and implementation in two sessions | `tests/publisher/test_session_binding.py::test_plan_and_implementation_in_two_sessions` |
