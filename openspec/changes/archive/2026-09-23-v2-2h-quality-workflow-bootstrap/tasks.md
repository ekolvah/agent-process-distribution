## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-2h-quality-workflow-bootstrap --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 153; verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 In `tests/publisher/test_reusable_workflows.py` add `test_quality_callee_runs_the_callers_commands` (design D1). It checks that `quality.yml` triggers only on `workflow_call`, declares `setup` (optional, default `""`) and `test` (required), and has permissions `contents`/`pull-requests`/`issues: read` and one job `quality`. It also checks the step order: the issue-link step equal to the one in `reusable-quality.yml`, checkout, `setup-python` 3.12, `setup` whose only `if` is `inputs.setup != ''`, and `test` with no `if`; neither command step has `continue-on-error`. Add `test_publisher_caller_reaches_callee_by_same_commit_path` (design D3). It checks that `agent-process.yml` triggers on `pull_request` with default types and has one job `agent-process` that uses `./.github/workflows/quality.yml` with the D3 `setup` and `test`. Add the pair `("agent-process.yml", "agent-process", "quality.yml")` to the schema and permission tests, and add `quality.yml` to `test_callees_declare_workflow_call_without_pull_request_trigger`. Verify that each new or extended test fails in its body
- [x] 1.2 In `tests/publisher/test_init.py::test_caller_inputs` require the job key `agent-process` and `uses` `ekolvah/agent-process-distribution/.github/workflows/quality.yml@v2.0.0` (design D4); verify that it fails
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py` with the node ids of 1.1–1.2; verify that it exits 0 with each test RED; commit as `test(distribution): RED for the quality workflow bootstrap`

## 2. Workflows

- [x] 2.1 Add `.github/workflows/quality.yml` per design D1; verify that `python -m pytest tests/publisher/test_reusable_workflows.py::test_quality_callee_runs_the_callers_commands tests/publisher/test_reusable_workflows.py::test_callees_declare_workflow_call_without_pull_request_trigger -q` is green (the tests that read `agent-process.yml` turn green in 2.2)
- [x] 2.2 Add `.github/workflows/agent-process.yml` per design D3, with a comment that names the same-commit path and the non-required bootstrap status, and add `NOT_REQUIRED["agent-process"]` in `.agent-process/scripts/check_branch_protection.py` per design D5; verify that `python -m pytest tests/publisher/test_reusable_workflows.py tests/agent_process/test_branch_protection.py -q` is green
- [x] 2.3 Update `skills/agent-process/templates/agent-process.yml` per design D4; verify that `python -m pytest tests/publisher/test_init.py -q` is green; commit Group 2 as `feat(distribution): land the quality callee and caller beside v1`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Confirm that `git diff --name-only origin/main` lists only the paths in the proposal's Impact and the change directory, and that `git diff origin/main -- .github/workflows/ci.yml .github/workflows/reusable-quality.yml .github/workflows/agent-review.yml .github/workflows/reusable-agent-review.yml` is empty
- [x] 3.3 Run `gh api repos/ekolvah/agent-process-distribution/rulesets/23732345 --jq '{enforcement, rules:[.rules[] | {type, checks: .parameters.required_status_checks}]}'`; verify that it still shows only `quality / quality` from integration `15368` as required, and keep the output for the PR report

## 4. Deliver

- [x] 4.1 With a clean worktree run `python skills/agent-process/scripts/archive_change.py v2-2h-quality-workflow-bootstrap`; verify that it applies the `distribution` delta, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "v2-2h-quality-workflow-bootstrap" --body-file <report>`. The report references tracking issue 153 without `Closes`. It carries the scenario → test map, the probe run ids and merge commit from design Observations, the output of 3.2's workflow diff and of 3.3, and, once they conclude, this PR's run ids for `quality / quality` and `agent-process / quality`. It names issue 154 (activation and the next-PR observation) and issue 115 (v1 deletion) as excluded ownership
- [ ] 4.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`, and answer P2/P3 without resolving. Run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- `distribution / Consumer test fails` → `tests/publisher/test_reusable_workflows.py::test_quality_callee_runs_the_callers_commands`
- `distribution / Consumer render` → `tests/publisher/test_init.py::test_caller_inputs`
- `distribution / Publisher PR` → `tests/publisher/test_reusable_workflows.py::test_publisher_caller_reaches_callee_by_same_commit_path`
