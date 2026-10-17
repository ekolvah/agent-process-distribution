## 0. Delivery start

- [x] 0.1 Run `agent-process start_change evaluate-ponytail --planner Claude --implementer Claude` (tracking issue 9), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: docs-only, `skip_specs`; the pilot runs are other changes with their own RED

## 2. Paper gate and setup

- [x] 2.1 Apply the paper gate of design decision 4 to the Context table and record each conflict's resolution here; on a conflict without one, record "not planned", tick group 3 as `skipped: paper gate`, and go to group 4
  - Gate passes: every conflict resolves without editing Ponytail's ruleset (`skills/ponytail/SKILL.md` at `v5.3.2`).
  - §I (test after code, fewer tests): §I takes precedence. Ponytail's "leaves one small test" is a floor that §I tightens (RED first, every behavioural change), not a ceiling, and its "Keep the structure the codebase already has: its layers, interfaces and conventions" covers the repository's own rules. Readings: RED first, tests added.
  - §V (`shortcut:` without an issue): §V takes precedence. A `shortcut: <the limit>, <when to upgrade>` comment that links its issue satisfies both. Reading: each `shortcut:` comment and its issue link.
  - §IV (silent `ponytail-subagent.js`): covered by the transcript check of decision 2 (task 3.3); stays a named risk of an optional plugin.
  - Ledger (outside the repository): closed on adoption by `ledger=false`; the pilot deletes its file (task 4.3).
- [x] 2.2 Confirm the pilot tasks with the person (design decision 1); for each, record A's PR, plan commit, base (`git rev-parse <plan commit>^`), `sessions` ids with their session structure and Claude Code build, and check each transcript reads `claude-opus-5-5`; then take both tasks' A readings (design decision 3) into a table here, before any B run
  - The person confirmed per-task-rates and planning-standard-first. Every transcript and subagent transcript below reads only `claude-opus-5-5`, Claude Code build 2.1.300.
  - per-task-rates (`task_id=issue-447`): PR 448, plan commit `5c177a9`, base `989e318ae06432b103f1d5906a12949c0ebebf69`. Sessions: `267d9d6c` propose (after a 4-turn discussion of the compaction panel; 5 subagents), `370c5085` apply started and interrupted after 2 minutes, `12151826` apply to the merge (4 subagents). Mid-delivery replan `d45d001` before the second RED. No merge of `main` into the branch.
  - planning-standard-first (`task_id=issue-451`): PR 454, plan commit `9dccf6c`, base `548ac6ee8c17dcc5621a4f28c328818120adce53`. Sessions: `478c943c` propose (after a 1-turn discussion; 2 mid-plan interventions, 1 compaction; 6 subagents), `64337745` apply (one mid-delivery correction after `/simplify`; questions after the settle; 4 subagents). One merge of `main` (`04fa88e`), after the settle.
  - Settle: the `clean:` line of `wait_for_pr` in the apply transcript, on the head below. Telemetry window: `start` (the `task-readings` rule) to the settle.

    | Reading | per-task-rates (A) | planning-standard-first (A) |
    | --- | --- | --- |
    | Settled head, time | `70265d5`, 2026-10-17T05:33:04Z | `0ab8fcd`, 2026-10-17T08:07:30Z |
    | `start`, `hours` | 04:18:36Z, 1.24 | 06:47:02Z, 1.34 |
    | `agent_hours` | 0.53 | empty |
    | `cost_usd`, `api_requests` | 6.1575, 145 | 11.4290, 215 |
    | `failed`, `denied`, `compactions` | 1, 0, 0 | 3, 3, 1 |
    | `plan_rounds`, `code_rounds` | 4, 1 | 4, 1 |
    | `lines`, changed files | 307, 11 | 530, 15 |
    | Added dependencies, new scripts | 0, 0 | 0, 0 |
    | `agent-review` findings P0/P1/P2/P3 | 0/0/0/0 (`claude-sonnet-5-5`) | 0/0/0/0 (`claude-sonnet-5-5`) |
    | CI on the settled head | success, 14 checks | success, 14 checks |
    | RED before the first implementation commit | yes (`9206123` before `dcdebed`) | yes (`65bb127` before `a30ecb4`) |
    | Test functions added | 1 | 2 |
    | `shortcut:` comments, without an issue | 0, 0 | 0, 0 |
    | `gap` | | `agent_hours: no reset-free active time of 64337745` (its first `type="cli"` sample is at 08:10:00Z, 2195 s) |
- [x] 2.3 Ask the person to confirm, then `git clone --depth 1 --branch v5.3.2 https://github.com/DietrichGebert/ponytail` into a new empty directory outside the repository; verify `git rev-parse HEAD` is `16352ac229eb08a9598dcae48fe9f2b342567d86` and `.claude-plugin/plugin.json` reads `"version": "5.3.2"`
  - Checkout: `C:/Users/jadow/AppData/Local/Temp/claude/c--Users-jadow-PycharmProjects-agent-process-distribution/a7c32878-ceda-4ccd-91ef-3765d104c514/scratchpad/ponytail-v5.3.2`; `HEAD` is `16352ac229eb08a9598dcae48fe9f2b342567d86`, `plugin.json` reads `"version": "5.3.2"`.
- [x] 2.4 Commit this group's ticks and records

## 3. Pilot runs

Arm B is the person's own CLI sessions, `claude --model claude-opus-5-5 --plugin-dir <ponytail checkout>`, in A's session structure (design decisions 1–2).

- [ ] 3.1 Task 1 setup, with the person's confirmation (design decision 2): once, the pilot ruleset on `refs/heads/pilot-base/**`, verified with `gh api repos/{owner}/{repo}/rules/branches/pilot-base/<slug>` after the push; `git push origin <base>:refs/heads/pilot-base/<slug>`; a pilot issue with A's issue title and body, its Area set with `set_status.py`; `git worktree add --detach <main>/.claude/worktrees/<slug>-base <base>`
- [ ] 3.2 Arm B: `/opsx:propose <slug>-pilot #<pilot issue>` in the base worktree; before apply, `git config branch.<slug>-pilot.gh-merge-base pilot-base/<slug>` and `gh issue develop <pilot issue> --name <slug>-pilot --base pilot-base/<slug>`; then `/opsx:apply <slug>-pilot` until `wait_for_pr` settles. Record the PR, the ids of its archived `sessions` file, its settle time, its PR base, and whether `git rev-parse <plan commit>^` equals A's base
- [ ] 3.3 Grep each B transcript and its `subagents/*.jsonl` for "You are a lazy senior developer" (rerun a session without it) and for `pull/<A PR>` and A's archive path (record a hit as a leak)
- [ ] 3.4 Take task 1's B readings (design decision 3, the §I/§V readings and the arm differences included) into a table here, and apply the rule of decision 4; when it already decides, tick 3.5 as `skipped: task 1 decides`
- [ ] 3.5 Task 2, as in 3.1–3.4
- [ ] 3.6 Ask the person, per task, whether they would have merged B instead of A, and record it; close B's PRs and pilot issues as not planned; with the person's confirmation delete each `pilot-base/<slug>`, the pilot ruleset and each base worktree
- [ ] 3.7 Commit this group's ticks and readings

## 4. Decision

- [ ] 4.1 Write `.agent-process/docs/adr/0046-ponytail-evaluation.md` from `template.md`: the comparison (design Context), the gate's resolutions, the method and its limits (decisions 1–2), the readings, the person's picks, the outcome. On adoption it names the install path of decision 4; on not planned, the deletion condition that would reopen the question. It cites no issue numbers; the delivery report links the pilot PRs
- [ ] 4.2 On adoption only: add one optional row with decision 4's install path to `skills/agent-process/SKILL.md` `## Install`, after verifying the pinned `ref` with `claude plugin marketplace add` and `claude plugin list` on a machine without that marketplace; otherwise record `not planned: no Install row`
- [ ] 4.3 Delete the Ponytail checkout and `~/.config/ponytail/band/`; commit the group with its ticks

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits
- [ ] 5.2 Run `openspec validate --strict --all`
- [ ] 5.3 Run the `test` that `.github/agent-process-quality.json` declares

## 6. Deliver

- [ ] 6.1 Run `agent-process archive_change evaluate-ponytail`, then `gh pr create --title "docs: evaluate-ponytail" --body-file <report>`; the report names tracking issue 9 as a plain reference, links the pilot PRs, carries the scenario-to-test map, and states the principles it interacts with (goal 2, §I, §IV, §V, §VII); it asks the person to post the decision on issue 9 and close it after merge
- [ ] 6.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- n/a: `skip_specs`
