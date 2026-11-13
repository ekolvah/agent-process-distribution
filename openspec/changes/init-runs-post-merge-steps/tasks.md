## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-runs-post-merge-steps --planner Claude --implementer Claude` (tracking issue 502), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 Extend the fake GitHub of `tests/publisher/init_harness.py`, reusing its `permissions`-by-token, `allow_auto_merge`, rules read and `tokened` log, with: rulesets list/`POST` as `FakeGh` of `tests/publisher/test_activate_protection.py` serves them, check runs, collaborator `PUT`, `user/repository_invitations` `GET`/`PATCH` per token, `updateProjectV2Collaborators` and `viewerCanUpdate`, `gh pr list --state merged` by head, `gh auth status --json hosts` and `gh auth token --user`; add `after-merge` to the `LINE` pattern
- [x] 1.2 In `tests/publisher/test_init_remote.py` add `test_post_merge_waits_for_the_merge` (a confirmed first run: the PR body lists the `after-merge` transitions; a rerun with the PR open after the agent account appears rewrites the body by `gh pr edit --body`), `test_post_merge_upgrade_done_is_unchanged`, `test_post_merge_steps_are_written` (one confirmed run after the merge, the fake serving both written rulesets back: order, a settings file in another JSON form keeps its keys, token absent from output, only post-merge writes and no push, person-side calls without `GH_TOKEN`/`GITHUB_TOKEN` and the agent's calls with its token from `tokened`, rerun all `unchanged`), `test_post_merge_protection_not_observed` (the refusal maps to `conflict protection`), `test_post_merge_agent_token_conflict` (a settings file git does not ignore, and one not a JSON object, each `conflict agent-token`, file unchanged), `test_agent_account` and `test_agent_account_ambiguous`; make `test_agent_identity_pending_is_manual` run without an agent account and name Prepare's login; delete `test_protection_inactive_is_manual` and `test_auto_merge_disallowed_is_manual`, and drop those rows from `test_observed_manual_rows_are_omitted` and `test_unreadable_manual_state_is_printed`
- [x] 1.3 In `tests/publisher/test_planning_workflow.py` rewrite `test_install_continues_past_the_installation_pr` (on `MERGED` step 5 runs `init --confirm`, `gh auth setup-git`, and asks at most the restart; no step 6) and `test_upgrade_approval_is_its_consent` (a dry-run that exits 0 is confirmed unasked whatever it plans; `gh pr merge --auto` only when `approval-ruleset` and `auto-merge` read `unchanged`; one that exits non-zero is shown and not confirmed; no "Ask once"); in `tests/publisher/test_skill_check.py` set `IDENTITY_FIX` to `Install step 5 of the agent-process skill`
- [x] 1.4 Run `agent-process check_red` with the node ids of 1.2 and 1.3 and commit RED with these ticks

## 2. Transitions

- [x] 2.1 In `skills/agent-process/scripts/manual.py` make `_identity_pending` take the token it reads with, print the identity row only without an agent account naming Prepare's login, remove the `protection` and `auto-merge` rows, and set `IDENTITY_FIX` there and in `skills/agent-process/templates/skill_check.py` (and its docstring) to "Install step 5 of the agent-process skill, then restart Claude Code"; verify `python -m pytest tests/publisher/test_skill_check.py tests/publisher/test_init_remote.py -q -k "identity or manual"` is green
- [x] 2.2 Add `skills/agent-process/scripts/post_merge.py` with `steps(target, merged_pr, agent)` per design D3–D6, finding the agent account and its token once; reading the merged installation PR itself, `protection` back with `activate_protection.read_back` and `approval-ruleset` back by `activate_protection.plan` reading `unchanged`; classify it in `init.py` before the onboarding steps and pass its `after-merge` lines to `onboarding._pr_step` for the PR body (and `gh pr edit --body` when an open PR's list differs), printing its lines after the onboarding steps, add `--agent` and the `after-merge` status, and update the docstring; verify `python -m pytest tests/publisher/test_init_remote.py -q` is green
- [x] 2.3 Verify `python -m pytest tests/publisher -q` is green, then commit the group with its ticks

## 3. Procedure and records

- [x] 3.1 In `skills/agent-process/SKILL.md` Install: step 2 names `--agent` only for `conflict agent`; step 3 confirms every dry-run that exits 0 unasked, the merge being the consent, runs `gh pr merge --auto` only when `approval-ruleset` and `auto-merge` read `unchanged`, and drops "Ask once"; step 4 drops the `protection`, `agent-identity` and `auto-merge` rows from the person's list and runs step 5 unasked on `MERGED`; steps 5–6 become step 5 (`init --confirm` with the same arguments, `gh auth setup-git`, the person restarts when `agent-token` was written); verify `grep -n "step 6\|activate_protection --pr" skills/agent-process/SKILL.md` prints nothing and `python -m pytest tests/publisher/test_planning_workflow.py -q` is green
- [x] 3.2 Amend ADR 0040 D1, D6, D7, its deletion condition and its Confirmation per design D1–D7; verify `grep -n "step 6" .agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` prints nothing, then commit the group with its ticks

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument and commit its edits
- [ ] 4.2 Run `openspec validate --strict --all` and the `test` that `.github/agent-process-quality.json` declares

## 5. Deliver

- [ ] 5.1 Run `agent-process archive_change init-runs-post-merge-steps`, then `gh pr create --title "feat: init-runs-post-merge-steps" --body-file <report>`. The report names tracking issue 502 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, goal 3 for the single consent, §IV for the token never printed and the visible conflicts, §VII)
- [ ] 5.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Before the merge | `tests/publisher/test_init_remote.py::test_post_merge_waits_for_the_merge` |
| distribution / Upgrade with the steps done | `tests/publisher/test_init_remote.py::test_post_merge_upgrade_done_is_unchanged` |
| distribution / After the merge | `tests/publisher/test_init_remote.py::test_post_merge_steps_are_written` |
| distribution / Quality not observed | `tests/publisher/test_init_remote.py::test_post_merge_protection_not_observed` |
| distribution / Token file not ignored | `tests/publisher/test_init_remote.py::test_post_merge_agent_token_conflict` |
| distribution / Dry-run conflict | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` |
| distribution / Agent account | `tests/publisher/test_init_remote.py::test_agent_account` |
| distribution / Several accounts | `tests/publisher/test_init_remote.py::test_agent_account_ambiguous` |
| distribution / Confirmed run | `tests/publisher/test_init_remote.py::test_remote_writes_are_project_and_pr` (unchanged) |
| distribution / Post-merge run | `tests/publisher/test_init_remote.py::test_post_merge_steps_are_written` |
| distribution / Dry-run | `tests/publisher/test_init_remote.py::test_dry_run_writes_nothing_remote` (unchanged), `::test_post_merge_waits_for_the_merge` |
| distribution / A clone with the agent's identity | `tests/publisher/test_activate_protection.py::test_a_clone_with_the_agent_identity` (unchanged), `tests/publisher/test_init_remote.py::test_post_merge_steps_are_written` |
| distribution / Identity pending | `tests/publisher/test_init_remote.py::test_agent_identity_pending_is_manual` |
| distribution / Identity holds | `tests/publisher/test_init_remote.py::test_agent_identity_holds` (unchanged) |
| distribution / Identity missing | `tests/publisher/test_skill_check.py::test_identity_missing` |
| distribution / Identity set | `tests/publisher/test_skill_check.py::test_identity_set` (unchanged) |
| distribution / Installation PR merged | `tests/publisher/test_planning_workflow.py::test_install_continues_past_the_installation_pr` |
| distribution / Unasked upgrade PR merged | `tests/publisher/test_planning_workflow.py::test_install_continues_past_the_installation_pr` |
| distribution / Upgrade with the agent's identity | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` |
| distribution / Write outside the PR or no agent identity | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` |
| review-and-merge / Auto-merge after the PR | `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (unchanged) |
| review-and-merge / Approval merges | n/a: platform behaviour, live confirmation in ADR 0040 |
