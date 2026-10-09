## 0. Delivery start

- [x] 0.1 Run `agent-process start_change evaluate-langfuse-backend --planner Claude --implementer Claude` for tracking issue 103. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/evaluate-langfuse-backend`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 no RED: docs-only (`skip_specs`), the product is an ADR from an owner-host spike; no process behaviour changes

## 2. Vetting (design D1–D3)

- [x] 2.1 Clone `langfuse/Claude-Observability-Plugin` into `evidence/langfuse-plugin/` of the main checkout (not this worktree), check out `v1.2.1`, and verify that `git rev-parse HEAD` prints `b5b7cc364996467e856dc17575b5674f4799ad87`; read `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `hooks/hooks.json` and `hooks/langfuse_hook.py` for every variable read, every network call and its host, and every file written; record the findings in `evidence/langfuse-vetting.md`. Verify that the note names each outbound host and each field sent
- [x] 2.2 Resolve the script's `langfuse>=4.7,<5` with `uv` on this host; record the version and its PyPI sha256 (from `https://pypi.org/pypi/langfuse/<version>/json`) and the `UV_EXCLUDE_NEWER` date in `evidence/langfuse-vetting.md`. Verify that `command -v uv` succeeds in Git Bash, so the `python3` fallback is not taken
- [x] 2.3 Write the payload record of D4 in `evidence/langfuse-vetting.md` and stop: ask the owner for Cloud (region) or self-hosted, the `CC_LANGFUSE_CAPTURE_IMAGES` value, and the reason. Verify that the owner's answer is recorded before any key is entered. Early exit (design D9): if 2.1 or 2.2 found a destination or field the owner cannot accept, or the owner declines every egress option, record the gate and go to 5.1

## 3. Install at local scope (design D3–D5)

- [x] 3.1 From the main checkout root, add the clone as a local marketplace and install `langfuse-observability` at `local` scope; add `UV_EXCLUDE_NEWER` (the 2.2 date) to the `env` block of the main checkout's `.claude/settings.local.json`; the owner enters the keys and base URL through the plugin's `userConfig` prompt, with `CC_LANGFUSE_DEBUG` on. Verify that the root `.claude/settings.local.json` carries the plugin entry and `UV_EXCLUDE_NEWER`; that `git status` in the main checkout shows no tracked file changed; that `env | grep -c '^LANGFUSE_'` in the launching shell prints 0; that a regex search for the key shape (`sk-lf-[0-9a-f]{8}-`) over `~/.claude/settings.json`, both `.claude/settings*.json` and, with `git grep -E`, the tracked tree finds nothing; and record in `evidence/langfuse-vetting.md` where the secret landed (Credential Manager or `~/.claude/.credentials.json`)
- [x] 3.2 Run one throwaway session from the main checkout launched with `CC_LANGFUSE_TRACE_TAGS=task:smoke,attempt:1` (Git Bash: `CC_LANGFUSE_TRACE_TAGS=task:smoke,attempt:1 claude`; PowerShell: `$env:CC_LANGFUSE_TRACE_TAGS='task:smoke,attempt:1'; claude; Remove-Item Env:CC_LANGFUSE_TRACE_TAGS`). Verify in the hook log that the turn was processed and that the `langfuse` version `uv` resolved for the hook (read from uv's cached environment for the script; record how in `evidence/langfuse-vetting.md`) is the 2.2 version, and in Langfuse that the trace carries both tags; if the tags are missing or wrong, read the hook log for the `CC_LANGFUSE_TRACE_TAGS` warning and the value received, fix the launch and rerun; only when the cause is in the plugin or the platform, record the AC3 finding, and check in the Langfuse UI whether M1–M6 can be filtered to a set of session ids without code — if not, take the D9 early exit to 5.1, otherwise continue with session-id filters

## 4. Measured tasks (design D5–D7)

Skipped on a D9 early exit: tick each task with `skipped: early exit at <task>`.

- [x] 4.1 The owner runs at least three real changes of this repository, each session launched from the main checkout with `CC_LANGFUSE_TRACE_TAGS=task:<change>,attempt:<n>` set for that launch only (launch syntax of 3.2); before each, `git -C evidence/langfuse-plugin rev-parse HEAD` prints the pinned commit and `git -C evidence/langfuse-plugin status --porcelain` prints nothing; record the change → session id list at each launch in `evidence/langfuse-readings.md`. Verify that every listed session has a trace in Langfuse with its tags (on the AC3 continue path of 3.2, by session id instead of tag)
- [x] 4.2 For each listed session, compare Langfuse input, output, cache-creation and cache-read totals with `npx -y ccusage@20.0.26 session --id <session-id> --offline --json`; record each divergence and its explanation in `evidence/langfuse-readings.md`. Verify that no session is missing on the Langfuse side, or that the drop is explained from the hook log
- [x] 4.3 Check that the sessions under each `task:<change>` tag in Langfuse are exactly the 4.1 list for that change (design D5) and record any mismatch (on the AC3 continue path, the 4.1 list is the grouping and this check is recorded as not applicable); then read M1, M3, M4, M5 and M6 (#99 definitions) per task from Langfuse filters, dashboards or its public API, with no script; the `langfuse` skill of `langfuse/skills` and `langfuse-cli` (versions recorded) may serve the reads, installed only after the last 4.1 session so no measured session loads them, with the keys in Git-ignored `evidence/.env` passed only to the reading command's environment. Verify that `evidence/langfuse-readings.md` holds the tag check and one row per task and metric with the value or `needs code: <why>`

## 5. Decision record (design D8)

- [x] 5.1 Write `.agent-process/docs/adr/0036-per-task-token-analysis-backend.md` in the MADR form of ADR 0029: criterion (AC5 of issue 103), pinned plugin commit and SDK version with digest, egress choice and reason, key location, AC3 and AC4 findings, the aggregated readings table (or, on a D9 early exit, the gate that failed and its observation), the verdict, the dropped Codex criterion, and the reconsider condition. Verify that `git grep --untracked -E 'sk-lf-[0-9a-f]{8}-|pk-lf-[0-9a-f]{8}-|@[a-z0-9-]+\.[a-z]{2,}'` over the ADR finds nothing, that it quotes no transcript text, and that every number in it is an aggregate
- [x] 5.2 Per the design's Migration Plan, keep the Langfuse installation in use (the owner continues with both backends) and remove only the spike's path-logging hooks from `.claude/settings.local.json` of the main checkout. Verify that the key-shape search of 3.1 still finds nothing in the tree. Commit the ADR as `docs(adr): per-task token analysis backend`

## 6. Verify

- [x] 6.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 6.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 7. Deliver

- [x] 7.1 With a clean worktree, run `agent-process archive_change evaluate-langfuse-backend`. Verify that it archives the change with no spec update, commits, and pushes the branch
- [ ] 7.2 Run `gh pr create --title "docs: evaluate-langfuse-backend" --body-file <report>`. The report references the tracking issue plainly (#103), never with `Closes`, states the verdict, and carries the scenario → test map and the deferrals (Codex criterion dropped; `CC_LANGFUSE_TRACEPARENT` left to #101)
- [ ] 7.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 7.4 Post the verdict with a link to the ADR on #101 and #99
- [ ] 7.5 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`): the change adds an ADR from an owner-host spike.
