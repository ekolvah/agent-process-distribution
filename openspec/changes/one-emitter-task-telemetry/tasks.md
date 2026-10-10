## 0. Delivery start

- [x] 0.1 Run `agent-process start_change one-emitter-task-telemetry --planner Claude --implementer Claude` for tracking issue 101. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/one-emitter-task-telemetry`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Write `tests/agent_process/test_task_session.py` against a signature stub of `.agent-process/scripts/task_session.py`. `TestComposeAttributes`: the project value is kept and `task_id=issue-N,attempt_id=K` is appended; a project value that already names `task_id` or `attempt_id` is rejected. `TestArguments`: a non-positive or non-integer `--issue` or `--attempt`, a missing `.claude/settings.json`, and a missing `env.OTEL_RESOURCE_ATTRIBUTES` each exit 2 with the cause on stderr, and the runner is not called. `TestLaunch`: the injected runner receives the command with `--settings` and one JSON argument after its first element, the JSON's `env` holds exactly `OTEL_RESOURCE_ATTRIBUTES` and the four design D2 trace variables with their D2 values, `--attempt` defaults to 1, and the runner's exit code is returned. Run `agent-process check_red tests/agent_process/test_task_session.py` and commit RED with this tick
- [x] 1.2 After the first gate run (D1, D5): each launch adds `service.instance.id=<uuid4>`, and a project value that names it is rejected. RED committed, then green

## 2. Launcher (design D1)

- [x] 2.1 Implement `task_session.py` with pure composition functions, a runner `Protocol`, and a `main(argv, runner)` that resolves the Git top level and reads `.claude/settings.json` as UTF-8. The CLI wires `subprocess.run` with an argument list and no shell. Verify with `python -m pytest tests/agent_process/test_task_session.py`. Commit

## 3. Host traces route (design D2, D3; Migration Plan 1–3)

- [x] 3.1 Back up `~/.config/alloy/config.alloy` and `run-alloy.ps1` with the suffix `.one-emitter.pre`. Record in `evidence/issue-101/host-change.md` the names (no values) of the User-scope variables that exist before the change. Verify that each backup is byte-identical (`cmp`)
- [x] 3.2 Write the candidate config of design D3: the `claude_code` receiver with a `traces` output only, followed by the transform, batch and Langfuse exporter with `otelcol.auth.basic` from `sys.env`; the Codex metric chain is gone. Validate it with the installed `alloy.exe validate --stability.level=experimental <candidate>` before replacing the config. Verify that validation exits 0 and that `grep -c -E 'include_metadata|codex|grafana' <candidate>` prints 0
- [x] 3.3 Set the Langfuse public and secret key variables at User scope from the owner's local Langfuse configuration, printing no value. Make `run-alloy.ps1` require them instead of `GRAFANA_CLOUD_*`. Restart Alloy through `run-alloy.ps1`. Verify that `127.0.0.1:4318` listens and that the Alloy log shows the `langfuse` exporter started with no error. On failure, run Migration Plan step 5 and stop

## 4. Live gate (design D5)

- [ ] 4.1 The owner launches one throwaway session from a fresh shell with `python .agent-process/scripts/task_session.py --issue 101 --attempt 1 -- claude`. It runs at least three turns, one tool call and one subagent. Record the session id in `evidence/issue-101/gate.md`. Verify gate (a) in Langfuse: every `claude_code.llm_request` is a generation with the four usage keys and the tags `task:issue-101` and `attempt:1`. If the cache keys are missing, apply the D3 fallback mapping, re-validate, restart, and repeat 4.1 once. If (a) still fails, or no trace arrives, run Migration Plan step 5, drop the D2 variables from the launcher and its test (test first), mark Group 5.1 `skipped: early exit at 4.1`, and continue with Group 6
- [ ] 4.2 Verify gate (b) in Grafana: `claude_code_token_usage_tokens_total{session_id="<id>"}` carries `task_id="issue-101"` and `attempt_id="1"`. Verify gate (c): for each of the four types, the sum of Langfuse usage over the session's generations (v2 observations API) equals the D5 Grafana total for that session. Record the query and both readings in `evidence/issue-101/gate.md`. If (c) diverges, first check the query's window and series selection, then stop before the PR and report the divergence to the owner
- [ ] 4.3 Launch a plain `claude` session without the launcher. Verify that no trace with its session id reaches Langfuse and that its Grafana series carries `vcs_repository_name` and no `task_id` label

## 5. Plugin removal (Migration Plan 4)

- [ ] 5.1 With the owner's confirmation, uninstall the Langfuse plugin and remove its entries from `.claude/settings.local.json` of the main checkout and from `pluginConfigs` in `~/.claude/settings.json`. Verify that `claude plugin list` no longer shows it and that a new session sends no hook trace (no `claude-code` tagged trace without `task:`)

## 6. Decision record and docs

- [ ] 6.1 Write `.agent-process/docs/adr/0037-one-emitter-feeds-both-telemetry-backends.md` in the MADR form of ADR 0036. It records the probe, D1–D4, the gate readings or the early-exit observation, the span field list sent to Langfuse, the D5 query, and the reconsider condition (a Claude Code release changes the trace schema; #99 catches it). Verify that `python -m pytest tests/agent_process/test_adr_records.py` passes
- [ ] 6.2 Rewrite `.agent-process/docs/telemetry-measurement-setup.md`. Add the traces route, the Alloy snippet without secrets, the launcher command for PowerShell and Git Bash, and the D5 per-session query. Remove the Codex route sections. Verify that `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py` passes, and that `git grep -E 'sk-lf-[0-9a-f]{8}-|pk-lf-[0-9a-f]{8}-|glc_'` over the tree finds nothing. Commit as `docs: one emitter feeds both telemetry backends`

## 7. Verify

- [ ] 7.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 7.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 8. Deliver

- [ ] 8.1 With a clean worktree, run `agent-process archive_change one-emitter-task-telemetry`. Verify that it archives the change with no spec update, commits, and pushes the branch
- [ ] 8.2 Run `gh pr create --title "chore: one-emitter-task-telemetry" --body-file <report>`. The report references the tracking issue plainly (#101), never with `Closes`. It carries the gate result, the scenario → test map and the deferrals: compaction signal and readings to #99, and Tempo
- [ ] 8.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 8.4 Close draft PR 104 with a comment naming the new PR as its replacement. Post on #99 the labels and tags it consumes and two rejection rules, naming #99 as their catcher: reject a measured window that contains a `vcs_repository_name` series of the measured repository without `task_id` (a session started without the launcher), and reject one whose per-type Langfuse usage differs from the D5 Grafana total (trace-schema drift). Verify that `gh pr view 104 --json state` prints `CLOSED`
- [ ] 8.5 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`): owner-side measurement tooling. Design D1 is covered by `tests/agent_process/test_task_session.py::TestComposeAttributes`, `::TestArguments` and `::TestLaunch`. D2–D5 cross into the third-party exporter and ingest, so they are covered by the live gate of Group 4 (`n/a` in CI: no test reads credentials or contacts Grafana or Langfuse).
