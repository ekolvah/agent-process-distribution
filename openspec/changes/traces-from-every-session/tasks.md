## 0. Delivery start

- [x] 0.1 Run `agent-process start_change traces-from-every-session --planner Claude --implementer Claude` for tracking issue 396. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/traces-from-every-session`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 no RED: the change removes a script with its tests and edits documents; the new trace route is host configuration, checked live in 2.4

## 2. Owner host (design D1, D2, D4, D5)

- [x] 2.1 With the person's confirmation, add the four trace variables of D1 and the three content variables of D4 to the `env` block of `~/.claude/settings.json`. Verified by 2.4
- [x] 2.2 With the person's confirmation, back up `~/.config/alloy/config.alloy`, remove its `langfuse.trace.tags` statement, add the D4 masking statement in a `span` and a `spanevent` context and, after the latter, the D4 copy of the `tool.output` event into `langfuse.observation.output`, with context-prefixed paths, remove the `logging` block (D5), and verify that `alloy fmt` and `alloy validate` accept the file and that the service's `/-/reload` answers `config reloaded`. Verified by 2.3 and 2.4
- [x] 2.3 Give the person the elevated PowerShell commands of D5 and have them run them: stop the hand-started `alloy.exe`, install Alloy silently with `/CONFIG` and `/DISABLEREPORTING=yes`, copy both Langfuse keys from the User scope into the service `Environment` value without printing them, set `sc.exe failure` to restart, and restart the service so it reads the keys. Verify that `Get-Service` shows the Alloy service Running with start type Automatic, that `127.0.0.1:4318` is held by the installed `alloy.exe`, and that the Alloy source of the Application event log shows the service start and no exporter error. If the service does not start, read that log before changing anything
- [x] 2.4 Ask the person to open a new VS Code extension session in this repository, run one prompt that runs `echo glc_MASKPROBE0000` and one subagent, and give its session id. Verify through `listObservations` filtered by that `sessionId`: its spans carry `langfuse.observation.usage_details` and no `langfuse.trace.tags`; the interaction span carries the prompt text, not `<REDACTED>`; the probe appears only as `<masked>`, the Bash observation's output included; the Bash, Read and Edit observations carry their tool output; the subagent's spans are there. Verify that the D3 LogQL token sums of the same session equal the Langfuse usage per type. Record the readings, without the session id, for the ADR. If a check fails, inspect the 2.1 file and the Alloy service before changing anything
- [x] 2.5 With the person's confirmation, stop the Alloy service, ask the person to open a new extension session and run one prompt, then start the service. Record the trace exporter lines of that session in `%APPDATA%/Code/logs/<latest>/window1/exthost/Anthropic.claude-code/Claude VSCode.log` and whether its Grafana token series arrived, for the design's "Alloy stopped" risk and ADR 0039. If the Grafana series stopped or the session was impaired, stop and raise it with the person before Group 3
- [x] 2.6 With the person's confirmation, delete `~/.config/alloy/run-alloy.ps1`, its `.pre` copy and `%LOCALAPPDATA%/GrafanaAlloy`

## 3. Repository (design D3)

- [x] 3.1 Delete `.agent-process/scripts/task_session.py` and `tests/agent_process/test_task_session.py`
- [x] 3.2 Add `.agent-process/docs/adr/0039-every-session-sends-traces.md` from `template.md` with D1–D5, pointing at the setup document for the variable listing, with the proposal's observations and the 2.4 and 2.5 readings. Its Considered Options carry the trace scope and the content rule that ADR 0037 chose and D1 and D4 reverse, and the plugin and straight-export routes of D5. Its reconsider conditions are the loss of `session.id` on spans, of Langfuse's `sessionId` mapping, or of the token fields on `api_request`; the Langfuse unit limit being reached (then a self-hosted Langfuse); a token found unmasked in Langfuse; and Langfuse reading the `tool.output` event itself or Claude Code emitting model responses without rerouting logs (D4). Add a one-line superseded note, pointing at 0039, for the launcher to ADRs 0037 and 0038 and for "No content" to ADR 0037
- [x] 3.3 Edit `.agent-process/docs/telemetry-measurement-setup.md`: remove every launcher, `task_id`, `attempt_id` and `service.instance.id` mention; move the seven variables of D1 and D4 to the transport text and name user settings in the traces row; say that a task's traces are the Langfuse sessions of its `sessions` ids; in the Alloy listing drop the tags statement and add the masking and `tool.output` copy statements of D4, and say that model responses do not reach Langfuse; replace the `run-alloy.ps1` sentence with the service of D5 and the "Prompts arrive as `<REDACTED>`" paragraph with the content variables of D4 and what reaches Loki unmasked; drop the sentence "Langfuse filters on trace tags, not on resource attributes, so the transform puts the tags on every span"; drop "and the per-task attributes are appended to the same variable" from the carrier paragraph of "Which label carries the project"; replace the "Per-session totals" PromQL with the `api_request` token sums of D3 and drop its `instance` caveat. No session id, key or account data. Verify that `git grep -n -i -E "task_session|launcher|launched|attempt_id|langfuse\.trace\.tags|per-task attributes|run-alloy|REDACTED" -- .agent-process/docs/telemetry-measurement-setup.md` prints nothing, and that `git ls-files .agent-process/scripts/task_session.py tests/agent_process/test_task_session.py` prints nothing. Commit as `chore: traces from every session`

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument and commit its edits
- [ ] 4.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 4.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `agent-process archive_change traces-from-every-session`. Verify that it archives the change with no spec update, commits and pushes the branch
- [ ] 5.2 Run `gh pr create --title "chore: traces-from-every-session" --body-file <report>`. The report names tracking issue #396 as a plain reference, never `Closes`, and carries the 2.4 and 2.5 observations and the scenario → test map
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`); see 1.1. D1–D5 are checked live in 2.3–2.5 and by
  the `git grep` in 3.3; the document by the doc header and link tests in 4.3.
