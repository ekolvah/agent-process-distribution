## 0. Delivery start

- [x] 0.1 Run `agent-process start_change evaluate-ponytail --planner Claude --implementer Claude` (tracking issue 9), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 no RED: docs-only, `skip_specs`; the pilot runs are other changes with their own RED

## 2. Paper gate and setup

- [ ] 2.1 Apply the paper gate of design decision 4 to the Context table and record each conflict's resolution here; on a conflict without one, record "not planned", tick group 3 as `skipped: paper gate`, and go to group 4
- [ ] 2.2 Confirm the pilot tasks with the person (design decision 1); for each, record A's PR, plan commit, base (`git rev-parse <plan commit>^`), `sessions` ids with their session structure and Claude Code build, and check each transcript reads `claude-opus-5-5`; then take both tasks' A readings (design decision 3) into a table here, before any B run
- [ ] 2.3 Ask the person to confirm, then `git clone --depth 1 --branch v5.3.2 https://github.com/DietrichGebert/ponytail` into a new empty directory outside the repository; verify `git rev-parse HEAD` is `16352ac229eb08a9598dcae48fe9f2b342567d86` and `.claude-plugin/plugin.json` reads `"version": "5.3.2"`
- [ ] 2.4 Commit this group's ticks and records

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
