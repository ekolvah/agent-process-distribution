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

- [x] 3.1 Task 1 setup, with the person's confirmation (design decision 2): once, the pilot ruleset on `refs/heads/pilot-base/**`, verified with `gh api repos/{owner}/{repo}/rules/branches/pilot-base/<slug>` after the push; `git push origin <base>:refs/heads/pilot-base/<slug>`; a pilot issue with A's issue title and body, its Area set with `set_status.py`; `git worktree add --detach <main>/.claude/worktrees/<slug>-base <base>`
  - per-task-rates: `pilot-base/per-task-rates` pushed at `989e318`; pilot issue 459 (title and body of A's issue, Area `Observability`); base worktree `.claude/worktrees/per-task-rates-base` at `989e318`. Ruleset `25298291`: `POST /rulesets` as `ekolvah-agent` returns 404 (no admin), so the person created it from `pilot-ruleset.json` (`pilot-base`, `refs/heads/pilot-base/**`: one approval with stale dismissal, required `agent-process / quality`, `agent-review / agent-review`, `pr-title`, no deletion rule, no bypass); `rules/branches/pilot-base/per-task-rates` lists its `pull_request` (1 approval) and `required_status_checks` rules.
- [x] 3.2 Arm B: `/opsx:propose <slug>-pilot #<pilot issue>` in the base worktree; before apply, `git config branch.<slug>-pilot.gh-merge-base pilot-base/<slug>` and `gh issue develop <pilot issue> --name <slug>-pilot --base pilot-base/<slug>`; then `/opsx:apply <slug>-pilot` until `wait_for_pr` settles. Record the PR, the ids of its archived `sessions` file, its settle time, its PR base, and whether `git rev-parse <plan commit>^` equals A's base
  - Departure, by the person's choice: arm B runs as headless sessions that Claude starts (`claude -p … --permission-mode auto`), not the person's own; build 2.1.296 (A: 2.1.300). Person turns are only the ones recorded here.
  - per-task-rates propose: session `b2a978c3`, 5 subagents, `approve` at architect-review round 2; it dropped the issue's `telemetry-measurement-setup.md` edit and hides rows with an empty `api_requests` from the two rate panels. Then `gh-merge-base` and `gh issue develop 459 --name per-task-rates-pilot --base pilot-base/per-task-rates`. Apply: session `c27baa31`. It paused at 7/10 (`start_change` failed at `gh issue develop` on the detached base and the session finished its steps by hand; the SessionStart hook reported no agent identity) to ask whether to re-import the live dashboard; one person-substitute turn answered "skip the live check, note it in the PR", since the shared dashboard carries A's merged version. A pending `ScheduleWakeup` kept the `-p` process alive; it was stopped and the session resumed with `--resume`.
  - per-task-rates result: PR 460 (base `pilot-base/per-task-rates`); archived `sessions` `b2a978c3`, `c27baa31`, both `claude-opus-5-5` only; plan commit `e05676f`, whose parent is A's base `989e318`. Settle: `wait_for_pr` returned at 2026-10-17T10:22:01Z on `87085bf` with every check green but `agent-process / link` (`PR 460 links no issue`) and `agent-process / quality`, which fails only on it. Cause: GitHub links a PR to an issue only when the PR targets the default branch, and B's base is `pilot-base/per-task-rates`; a setup artifact, not fixed, since the PR closes unmerged.
- [x] 3.3 Grep each B transcript and its `subagents/*.jsonl` for "You are a lazy senior developer" (rerun a session without it) and for `pull/<A PR>` and A's archive path (record a hit as a leak)
  - per-task-rates propose `b2a978c3`: the ruleset line in the transcript and in all 5 subagent transcripts. Leak: one `git log` output held the subject `feat: per-task-rates (#448)`; no `pull/448`, no archive path, and no command read that commit.
  - per-task-rates apply `c27baa31`: the ruleset line in the transcript and in all 4 subagent transcripts; no leak (the archive-path hits are B's own `2026-10-17-per-task-rates-pilot`).
- [x] 3.4 Take task 1's B readings (design decision 3, the §I/§V readings and the arm differences included) into a table here, and apply the rule of decision 4; when it already decides, tick 3.5 as `skipped: task 1 decides`
  - Telemetry label `vcs_repository_name="ekolvah/agent-process-distribution"`, window from `start` to the settle above.

    | Reading | per-task-rates (A) | per-task-rates (B) |
    | --- | --- | --- |
    | Settled head, time | `70265d5`, 05:33:04Z | `87085bf`, 10:22:01Z |
    | `start`, `hours` | 04:18:36Z, 1.24 | 09:37:27Z, 0.74 |
    | `agent_hours` | 0.53 | 0.36 |
    | `cost_usd`, `api_requests` | 6.1575, 145 | 6.9422, 141 |
    | `failed`, `denied`, `compactions` | 1, 0, 0 | 1, 0, 0 |
    | `plan_rounds`, `code_rounds` | 4, 1 | 2, 1 |
    | `lines`, changed files | 307, 11 | 355, 10 |
    | Added dependencies, new scripts | 0, 0 | 0, 0 |
    | `agent-review` findings P0/P1/P2/P3 | 0/0/0/0 (`claude-sonnet-5-5`) | 0/0/0/0 (`claude-sonnet-5-5`) |
    | CI on the settled head | success, 14 checks | 12 of 14 success; `link` and `quality` fail on the pilot base |
    | RED before the first implementation commit | yes | yes (`03c4918` before `c5b97f0`) |
    | Test functions added | 1 | 1 |
    | `shortcut:` comments, without an issue | 0, 0 | 0, 0 |

  - Arm differences: no commit to `REVIEW_CONTRACT.md` or the review workflows since A's review; build 2.1.296 against 2.1.300; headless sessions with one person-substitute turn; no agent identity, so B's commits and PR carry the person's name; B's scope is narrower (no `telemetry-measurement-setup.md` edit).
  - Rule of decision 4: B meets every floor (findings, rounds, RED first, tests, `shortcut:`; CI green but for the setup-caused `link`) but neither costs less (6.9422 against 6.1575) nor changes fewer lines (355 against 307), with a narrower scope. Task 1 decides: not planned.
- [x] 3.5 Task 2, as in 3.1–3.4
  - Departure, by the person's choice: task 2 runs although task 1 decides, in case task 1 is not representative.
  - Setup: `pilot-base/planning-standard-first` pushed at `548ac6e`, covered by ruleset `25298291`; pilot issue 461 (title and body of A's issue, Area `Process quality`); base worktree `.claude/worktrees/planning-standard-first-base`.
  - Leaked run, discarded: propose `523003a5` (slug `planning-standard-first-pilot`; `approve` at round 2; `/simplify` run by itself instead of the four agents) read `git log origin/main`, then `git show --stat` of A's merge commit and `gh pr view 454`, and reported it had not; apply `034ec719` found A's delivery on `origin/main` and stopped at 0/14 to propose closing the issue as a duplicate. Cost 2.40 + 0.90. Its change is kept outside the repository; its branch (no commits past the base) and worktree are deleted.
  - Rerun, blind: slug `pilot-461`; each session gets `--append-system-prompt` (a blind re-delivery from the base: read nothing made after it; the PR targets the pilot base; never `ScheduleWakeup`) and `--disallowedTools` on `gh pr view|diff 454`, `gh issue view 451`, `gh pr list`, `gh issue list`, `gh search` and `git show` of A's merge commit. Propose: session `918bc8c1`, no leak, `approve` at architect-review round 2, 5 subagents; it also published a private artifact explaining the plan. Then `gh-merge-base` and `gh issue develop 461 --name pilot-461 --base pilot-base/planning-standard-first`. Apply: session `a4823b07`.
  - Result: PR 462 (base `pilot-base/planning-standard-first`, branch `pilot-461-redelivery` made by hand, since `start_change` failed as in task 1). Plan commit `c282ef6`, whose parent is A's base `548ac6e`. The ruleset line is in both transcripts and all their subagent transcripts. No leak in the apply or its 4 subagents. Both sessions read only `claude-opus-5-5` on build 2.1.296, with no person-substitute turn. The archived `sessions` file also lists the discarded `523003a5` and `034ec719`; the readings take only `918bc8c1` and `a4823b07`. Settle: `wait_for_pr` returned at 2026-10-17T11:31:09Z on `7e99ad9`, with `link` and `quality` failing as in task 1.

    | Reading | planning-standard-first (A) | planning-standard-first (B) |
    | --- | --- | --- |
    | Settled head, time | `0ab8fcd`, 08:07:30Z | `7e99ad9`, 11:31:09Z |
    | `start`, `hours` | 06:47:02Z, 1.34 | 10:53:25Z, 0.63 |
    | `agent_hours` | empty | empty |
    | `cost_usd`, `api_requests` | 11.4290, 215 | 7.6205, 141 |
    | `failed`, `denied`, `compactions` | 3, 3, 1 | 1, 0, 0 |
    | `plan_rounds`, `code_rounds` | 4, 1 | 2, 1 |
    | `lines`, changed files | 530, 15 | 435, 15 |
    | Added dependencies, new scripts | 0, 0 | 0, 0 |
    | `agent-review` findings P0/P1/P2/P3 | 0/0/0/0 | 0/0/1/0 (answered, thread left open) |
    | CI on the settled head | success, 14 checks | 12 of 14 success; `link` and `quality` fail on the pilot base |
    | RED before the first implementation commit | yes | yes (`56929b7` before `a272e10`) |
    | Test functions added | 2 | 3 |
    | `shortcut:` comments, without an issue | 0, 0 | 0, 0 |
    | `gap` | as above | `agent_hours: no reset-free active time of a4823b07` (`918bc8c1`: 506 s) |

  - Arm differences: as in task 1. Both B sessions are headless, with a blinding system prompt and deny-list. A's sessions had 2 mid-plan interventions, 1 compaction and 3 denials. B's run came after a discarded leaked attempt on the same issue.
  - Rule of decision 4: B meets every floor (CI green but for the setup-caused `link`). It costs less (7.6205 against 11.4290) and changes fewer lines (435 against 530). Task 2 passes. Task 1 fails, and the rule requires each task, so the outcome stays not planned.
- [x] 3.6 Ask the person, per task, whether they would have merged B instead of A, and record it; close B's PRs and pilot issues as not planned; with the person's confirmation delete each `pilot-base/<slug>`, the pilot ruleset and each base worktree
  - The person gave no per-task merge verdict. After the readings and the bespoke comparison (Ponytail replaces none of the process's scripts or gates; it overlaps only their prose), they decided not to install it and asked for the cleanup.
  - Closed unmerged: PRs 460 (auto-merge disabled first) and 462. Closed as not planned: issues 459 and 461. Deleted: base worktrees `per-task-rates-base` and `planning-standard-first-base`, the pilot worktree `per-task-rates-pilot`, local branches `per-task-rates-pilot` and `pilot-461-redelivery` (`-d`, both at their upstream), and on `origin` `per-task-rates-pilot`, `pilot-461`, `pilot-461-redelivery` and both `pilot-base/<slug>`. B's heads stay reachable as `refs/pull/<PR>/head`. Ruleset `25298291` is the person's to delete (the agent has no admin).
- [x] 3.7 Commit this group's ticks and readings

## 4. Decision

- [x] 4.1 Write `.agent-process/docs/adr/0046-ponytail-evaluation.md` from `template.md`: the comparison (design Context), the gate's resolutions, the method and its limits (decisions 1–2), the readings, the person's picks, the outcome. On adoption it names the install path of decision 4; on not planned, the deletion condition that would reopen the question. It cites no issue numbers; the delivery report links the pilot PRs
- [x] 4.2 On adoption only: add one optional row with decision 4's install path to `skills/agent-process/SKILL.md` `## Install`, after verifying the pinned `ref` with `claude plugin marketplace add` and `claude plugin list` on a machine without that marketplace; otherwise record `not planned: no Install row`
  - not planned: no Install row
- [x] 4.3 Delete the Ponytail checkout and `~/.config/ponytail/band/`; commit the group with its ticks
  - Deleted the checkout, the discarded leaked change kept beside it, and `~/.config/ponytail/` (it held only `band/`, created by the pilot).

## 5. Verify

- [x] 5.1 Run `/simplify` without an argument and commit its edits
  - The diff is docs only (ADR, tasks, proposal, design), so the four angles were reviewed inline without the agents (goal 2); no edits.
- [x] 5.2 Run `openspec validate --strict --all`
  - 9 passed, 0 failed.
- [x] 5.3 Run the `test` that `.github/agent-process-quality.json` declares
  - `ci_check.py` first failed `test_every_internal_link_resolves`: the proposal and design pointed at the Install anchor by a bare path, which resolves against the change directory. Both now name the skill's `## Install` section instead, so the wording survives the archive move. The test passes.

## 6. Deliver

- [x] 6.1 Run `agent-process archive_change evaluate-ponytail`, then `gh pr create --title "docs: evaluate-ponytail" --body-file <report>`; the report names tracking issue 9 as a plain reference, links the pilot PRs, carries the scenario-to-test map, and states the principles it interacts with (goal 2, §I, §IV, §V, §VII); it asks the person to post the decision on issue 9 and close it after merge
- [ ] 6.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- n/a: `skip_specs`
