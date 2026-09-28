## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py releases-through-auto-update --planner Claude --implementer Claude` for tracking issue 199. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/releases-through-auto-update`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py` add `test_marketplace_follows_stable` (D1): in `init._render_settings(init.VERSION)` and in `init._render_settings("0.0.1")` the `agent-process-marketplace` source's `ref` is `"stable"` and the entry's `autoUpdate` is `True`. In `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed` expect `"ref": "stable"` and `"autoUpdate": true` in the rendered entry; in `tests/publisher/test_init_config.py::test_rerender_replaces_only_owned_content` expect `ref == "stable"` and `autoUpdate is True` where the consumer entry held `v1.9.0`. In `tests/publisher/test_init_remote.py::test_manual_actions_are_printed` expect exactly one `manual plugin-channel: ` row naming `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"` and `Enable auto-update`, and no logged command whose program is `claude`. Verify with the 1.5 run
- [x] 1.2 In `tests/publisher/test_reusable_workflows.py` add `test_release_workflow_moves_stable` (D2): the step after the auto-merge step has `if: steps.release.outputs.release_created == 'true'`, `GH_TOKEN` = `${{ secrets.RELEASE_PLEASE_TOKEN }}`, `SHA` = `${{ steps.release.outputs.sha }}`, and its `run` PATCHes `git/refs/heads/stable` with `sha="$SHA"` and `force=false` and names no `--force`/`force=true`; the step has no `continue-on-error` and its `run` contains no `|| true` and no `set +e`, so a refused update fails the run. Verify with the 1.5 run
- [x] 1.3 In `tests/publisher/test_init_config.py` add `test_dependabot_leaves_process_refs_to_install` (D3): after a fresh confirmed install, the `github-actions` entry of the written `.github/dependabot.yml` has `ignore == [{"dependency-name": "ekolvah/agent-process-distribution*"}]`. Verify with the 1.5 run
- [x] 1.4 D4: in `tests/publisher/test_start_change.py` set `_SKILL_FIX = "claude plugin update agent-process@agent-process-marketplace --scope"` and assert `"#v"` is not in the drift message; in `tests/publisher/test_planning_workflow.py::test_install_names_the_skill_marker` expect `claude plugin update agent-process@agent-process-marketplace`, `stable` and `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"` in the Install section, `plugin-channel` in Install step 4 (the step that relays the `manual` rows), and no `/plugin marketplace update`. Verify with the 1.5 run
- [x] 1.5 Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_plugin.py::test_marketplace_follows_stable tests/publisher/test_init_remote.py::test_installed_footprint_is_closed tests/publisher/test_init_config.py::test_rerender_replaces_only_owned_content "tests/publisher/test_init_remote.py::test_manual_actions_are_printed[--dry-run]" "tests/publisher/test_init_remote.py::test_manual_actions_are_printed[--confirm]" tests/publisher/test_reusable_workflows.py::test_release_workflow_moves_stable tests/publisher/test_init_config.py::test_dependabot_leaves_process_refs_to_install "tests/publisher/test_start_change.py::test_release_drift[newer-start_change]" "tests/publisher/test_start_change.py::test_release_drift[newer-create_tracking_issue]" tests/publisher/test_planning_workflow.py::test_install_names_the_skill_marker` and verify every test fails in its body (only the `newer` params of `test_release_drift` change; the other ten stay green and are not named). Commit as `test(distribution): releases reach consumers through auto-update`

## 2. Channel (D1, D2)

- [x] 2.1 `skills/agent-process/templates/settings.json`: source `"ref": "stable"`, entry `"autoUpdate": true`. Verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_init_remote.py tests/publisher/test_init_config.py tests/publisher/test_init.py -q` passes
- [x] 2.2 `.github/workflows/release-please.yml`: after the auto-merge step add `Move stable to the release` per D2 (env `GH_TOKEN`, `GH_REPO`, `SHA`; `gh api -X PATCH "repos/$GH_REPO/git/refs/heads/stable" -f sha="$SHA" -F force=false`) and extend the header comment by one line. Verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes. Commit as `feat(distribution): the marketplace follows the stable channel`

## 3. Dependabot and drift fix (D3, D4)

- [x] 3.1 `skills/agent-process/templates/dependabot.yml`: inside the marker block add the `ignore` of D3. Verify `python -m pytest tests/publisher/test_init_config.py tests/publisher/test_init_conflicts.py -q` passes
- [x] 3.2 `skills/agent-process/scripts/init.py::release_drift`: the skill-older fix names `claude plugin update agent-process@agent-process-marketplace --scope <user|project>` and a restart (D4); `_manual` gains the `plugin-channel` row of D1 and the module docstring names it among the `manual` rows. `skills/agent-process/SKILL.md` Install step 4: the `manual` rows it relays name the `plugin-channel` row (once per machine, outside any project) beside `project-*` and `review-secret`; Install, last paragraph: the marketplace follows `stable` with auto-update; the plugin update fix; the D5 migration steps in one sentence. Verify `python -m pytest tests/publisher/test_start_change.py tests/publisher/test_planning_workflow.py tests/publisher/test_init_remote.py -q` passes. Commit as `feat(distribution): release drift names a plugin update`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py releases-through-auto-update`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: releases-through-auto-update" --body-file <report>`. The report names tracking issue #199 as a plain reference (never `Closes`), carries the scenario → test map, the D5 block `BEGIN_COMMIT_OVERRIDE` / `feat!: releases-through-auto-update` / blank line / `BREAKING CHANGE: <D5 migration steps>` / `END_COMMIT_OVERRIDE`, and notes for the person: the first release after merge proves the `stable channel` ruleset's admin bypass (the `Move stable` step succeeds); the drive-letter duplicate records are a follow-up issue
- [ ] 5.3 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Channel render → `tests/publisher/test_plugin.py::test_marketplace_follows_stable`; `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed`
- `distribution` / Machine channel step → `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`
- `distribution` / Release created → `tests/publisher/test_reusable_workflows.py::test_release_workflow_moves_stable`
- `distribution` / No release → `tests/publisher/test_reusable_workflows.py::test_release_workflow_moves_stable` (the step's `if`)
- `distribution` / Dependabot render → `tests/publisher/test_init_config.py::test_dependabot_leaves_process_refs_to_install`
- `distribution` / Release recorded → `tests/publisher/test_init_config.py::test_config_block_records_release` (unchanged)
- `distribution` / Release drift → `tests/publisher/test_start_change.py::test_release_drift`
- `distribution` / Publisher checkout → `tests/publisher/test_start_change.py::test_publisher_checkout_is_exempt` (unchanged)
