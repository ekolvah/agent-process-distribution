## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-2i-protection-activation --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 154; verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_activate_protection.py` with a fake `Gh` that answers by command shape and records every call. Add a signature stub `skills/agent-process/scripts/activate_protection.py` whose `main` raises `NotImplementedError`, so that each test fails in its body. Add one test per scenario in the map below (design D2–D4), and parametrize each over every case its scenario or requirement names. `test_context_not_observed` covers four cases: a base other than the default branch, no run, a run that did not succeed, and another app. `test_ambiguous_rulesets` covers two rulesets and one ruleset not owned by the repository, each under `--dry-run` and `--confirm`. `test_read_back_mismatch` covers one case per D4 field: the ref include, the ref exclude, enforcement, bypass, and each of the four rule types. It also covers strict, the context, and the integration. `test_no_ruleset_yet` asserts the create rollback line. Each test asserts the exit code and the printed lines. Wherever the scenario says "every command is a read", it also asserts that the recorded calls hold no `-X POST|PUT|PATCH|DELETE`
- [x] 1.2 In `tests/publisher/test_reusable_workflows.py` add `test_publisher_driver_keeps_a_same_head_catcher` (design D5). It imports `REQUIRED_CONTEXTS` from `.agent-process/scripts/check_branch_protection.py` and asserts that it contains `quality / quality` or `agent-review / agent-review`. Verify that it passes on `main`: it pins an existing state, so the task records `no RED: pins the live declaration the activation relies on`. Recorded: passes on `main`; `test_delivery_scripts.py` only lists the script, which the stub satisfies, so its update carries no RED either
- [x] 1.3 In `tests/publisher/test_plugin.py` and `tests/publisher/test_delivery_scripts.py`, add `activate_protection.py` to `MOVED_SCRIPTS` and `ruleset.json` to `TEMPLATES`, and reduce the forbidden tokens to `("hook",)` (design D1); verify that they fail
- [x] 1.4 Run `python skills/agent-process/scripts/check_red.py` with the node ids of 1.1 and 1.3; verify that it exits 0 with each test RED; commit as `test(distribution): RED for protection activation`

## 2. Activation script

- [ ] 2.1 Add `skills/agent-process/templates/ruleset.json` per design D3 (PR 151's body with the `__DEFAULT_BRANCH__`, `__CONTEXT__` and `__INTEGRATION__` placeholders); verify that `python -m pytest tests/publisher/test_plugin.py -q` is green
- [ ] 2.2 Implement the preflight per design D2; verify that `python -m pytest tests/publisher/test_activate_protection.py -k "caller_absent or context_not_observed" -q` is green
- [ ] 2.3 Implement the plan, the owned-field comparison, the conflict refusal, and the classic read per design D3; verify that `python -m pytest tests/publisher/test_activate_protection.py -k "dry_run or ambiguous or rerun" -q` is green
- [ ] 2.4 Implement the confirmed `POST`/`PUT` with its temporary input and the read-back per design D3–D4; verify that `python -m pytest tests/publisher/test_activate_protection.py tests/publisher/test_delivery_scripts.py -q` is green; commit Group 2 as `feat(distribution): activate protection after observed quality`

## 3. Pointers

- [ ] 3.1 Add step 5 to `## Install` in `skills/agent-process/SKILL.md` per design D6. Update the reason of `NOT_REQUIRED["agent-process"]` in `.agent-process/scripts/check_branch_protection.py` per design D5. Add the ADR 0027 row and the deletion condition per design D6. Verify that `python -m pytest tests/publisher tests/agent_process/test_branch_protection.py -q` is green, then commit as `docs(distribution): install step and ADR row for protection activation`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 5. Deliver

- [ ] 5.1 With a clean worktree run `python skills/agent-process/scripts/archive_change.py v2-2i-protection-activation`; verify that it applies the `distribution` delta, commits the archive, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "v2-2i-protection-activation" --body-file <report>`. The report references tracking issue 154 without `Closes`, and carries the scenario → test map and the design's Observations. It names issue 114, issue 115, issue 117, and the follow-up issue (classic `quality / quality` and `ci.yml`) as excluded ownership
- [ ] 5.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`, and answer P2/P3 without resolving
- [ ] 5.4 Once `wait_for_pr` has settled a head with `agent-process / quality` green, follow the design's Migration Plan. Run `python skills/agent-process/scripts/activate_protection.py --pr <PR> --dry-run` and verify that it prints `planned update 23732345` with the context change and the rollback line. Show the whole output to the person, and run `--confirm` only on their yes. Verify `written: ruleset 23732345`, then a second `--dry-run` printing `unchanged`, and verify that `gh api repos/ekolvah/agent-process-distribution/branches/main/protection --jq '.required_status_checks.checks'` still lists `quality / quality` and `agent-review / agent-review`. Add the three outputs to the PR body
- [ ] 5.5 Run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- `distribution / Quality check on a PR` → `tests/publisher/test_reusable_workflows.py::test_quality_executes_a_trusted_driver_against_the_pr_worktree`
- `distribution / PR weakens its own driver` → `tests/publisher/test_reusable_workflows.py::test_publisher_driver_keeps_a_same_head_catcher`
- `distribution / Caller absent` → `tests/publisher/test_activate_protection.py::test_caller_absent`
- `distribution / Context not observed` → `tests/publisher/test_activate_protection.py::test_context_not_observed`
- `distribution / Dry-run` → `tests/publisher/test_activate_protection.py::test_dry_run`
- `distribution / No ruleset yet` → `tests/publisher/test_activate_protection.py::test_no_ruleset_yet`
- `distribution / Live ruleset differs` → `tests/publisher/test_activate_protection.py::test_live_ruleset_differs`
- `distribution / Rerun` → `tests/publisher/test_activate_protection.py::test_rerun`
- `distribution / Ambiguous rulesets` → `tests/publisher/test_activate_protection.py::test_ambiguous_rulesets`
- `distribution / Read-back mismatch` → `tests/publisher/test_activate_protection.py::test_read_back_mismatch`
