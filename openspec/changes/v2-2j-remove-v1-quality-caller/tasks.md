## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-2j-remove-v1-quality-caller --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 166. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 In `.agent-process/scripts/check_branch_protection.py`, add `RULESET_CONTEXTS = ("agent-process / quality",)` beside `REQUIRED_CONTEXTS` (design D2). This is declaration data that no code reads yet. In `tests/agent_process/test_review_gate.py`, make `_checks` grade `(*REQUIRED_CONTEXTS, *RULESET_CONTEXTS)`, build `_pr_payload`'s `statusCheckRollup` from both lists, and expect both lists in `test_non_checkrun_rollup_entries_are_ignored`. These fixture moves stay green on the RED head, because the gate ignores extra contexts. Rename `test_red_deterministic_check_is_fix_blocking_and_names_it` to `test_red_ruleset_context_is_fix_blocking_and_names_it`: it overrides `agent-process / quality` to `FAILURE` and asserts `fix-blocking` with that name in the reason. Add an `absent-ruleset-context` case to `test_pending_or_absent_required_context_is_review_pending` that drops `agent-process / quality` and asserts `review-pending` naming it
- [x] 1.2 In `tests/publisher/test_reusable_workflows.py`, add `test_quality_runs_once_per_pr` (design D1). In `tests/agent_process/test_branch_protection.py`, change `test_controller_gate_is_not_a_required_context` to expect `("agent-review / agent-review",)`
- [x] 1.3 In `tests/agent_process/test_branch_protection.py`, rewrite the `TestProtectionInstallation` fixtures so that they do not depend on the tuple's length (design, Risks): `_protected_policy` carries only `consumer / test`, the add test expects all of `REQUIRED_CONTEXTS` as missing, and the strict/admin and rerun tests extend with all of `REQUIRED_CONTEXTS`. Tighten `test_publisher_driver_keeps_a_same_head_catcher` to `"agent-review / agent-review" in REQUIRED_CONTEXTS` (design D3). Verify that `python -m pytest tests/agent_process/test_branch_protection.py::TestProtectionInstallation tests/publisher/test_reusable_workflows.py::test_publisher_driver_keeps_a_same_head_catcher -q` passes on this head, and record `no RED: composition-independent fixtures and a pin that main already satisfies`
- [x] 1.4 Run `python skills/agent-process/scripts/check_red.py` with the node ids of 1.1 and 1.2. Verify that it exits 0 with each test RED, then commit as `test(distribution): RED for removing the v1 quality caller`

## 2. One quality run, gate on both lists

- [x] 2.1 Delete `.github/workflows/ci.yml`. Remove the `ci.yml` reads from `tests/publisher/test_reusable_workflows.py` and `tests/agent_process/test_ci_check.py` (design D1). Set `REQUIRED_CONTEXTS = ("agent-review / agent-review",)` (design D2). Verify that `python -m pytest tests/publisher/test_reusable_workflows.py tests/agent_process/test_ci_check.py tests/agent_process/test_branch_protection.py -q` is green
- [x] 2.2 Make `review_gate.evaluate` judge `(*REQUIRED_CONTEXTS, *RULESET_CONTEXTS)` (design D2), import `RULESET_CONTEXTS` on both import paths, and update the module docstring's shared-data sentence. Verify that `python -m pytest tests/agent_process/test_review_gate.py -q` is green
- [x] 2.3 Edit the `agent-process.yml` header comment and the `check_secrets` docstring (design D4). Verify that `python -m pytest tests/publisher tests/agent_process -q` is green, then commit Group 2 as `feat(distribution): run quality once per PR`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py v2-2j-remove-v1-quality-caller`. Verify that it applies the `distribution` and `review-and-merge` deltas, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "v2-2j-remove-v1-quality-caller" --body-file <report>`. The report references tracking issue 166 without `Closes`. It carries the scenario → test map and the design's Observations, and names issues 114, 115, and 117 as excluded ownership
- [ ] 4.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving
- [ ] 4.4 Once `wait_for_pr` has settled a head with `agent-process / quality` and `agent-review / agent-review` green, follow the design's Migration Plan. Show the person the `DELETE` command and its rollback, and let them run it. Then verify that `gh api repos/ekolvah/agent-process-distribution/branches/main/protection --jq '.required_status_checks.checks'` lists only `agent-review / agent-review`, and add that output to the PR body
- [ ] 4.5 Run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- `distribution / PR weakens its own driver` → `tests/publisher/test_reusable_workflows.py::test_publisher_driver_keeps_a_same_head_catcher`
- `distribution / Quality runs once per PR` → `tests/publisher/test_reusable_workflows.py::test_quality_runs_once_per_pr`
- `review-and-merge / Missing required context` → `tests/agent_process/test_branch_protection.py::TestPrePushHook::test_drift_blocks_push_without_running_ci_check`
- `review-and-merge / Ruleset context red` → `tests/agent_process/test_review_gate.py::TestVerdict::test_red_ruleset_context_is_fix_blocking_and_names_it`
