## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py remove-reusable-quality --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 205. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_reusable_workflows.py::test_the_v1_quality_callee_is_gone`: assert `WORKFLOWS / "reusable-quality.yml"` does not exist, and that no file under `.github/workflows/` or `.agent-process/copier-answers.yml` contains `reusable-quality`. Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_reusable_workflows.py::test_the_v1_quality_callee_is_gone` and verify it fails in the test body; commit as `test: the v1 quality callee is gone`

## 2. Removal

- [x] 2.1 In `tests/publisher/test_reusable_workflows.py`: delete `test_quality_executes_a_trusted_driver_against_the_pr_worktree` and `test_quality_installs_product_dependencies_when_present`; drop `reusable-quality.yml` from the list in `test_callees_declare_workflow_call_without_pull_request_trigger` and from the filter set in `test_quality_runs_once_per_pr`; retarget `test_quality_verifies_the_pr_links_its_issue_before_the_driver` to `quality.yml`, keeping every assertion on the step and the permissions, and asserting on the raw step list of the `quality` job (the `_steps` helper drops the unnamed checkout) that the link step comes before the first `actions/checkout` step; in `test_quality_callee_runs_the_callers_commands`, replace the comparison with the removed file's step by `steps[0]["name"] == "Verify the PR links its issue"`. Verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes except `test_the_v1_quality_callee_is_gone`
- [x] 2.2 Delete `.github/workflows/reusable-quality.yml`, reword the link-step comment of `.github/workflows/quality.yml` so that it no longer names the file (keep the ADR 0027 / v2-2c reference), and delete the `quality:` line under `workflow_references` in `.agent-process/copier-answers.yml`. Verify `python -m pytest tests/publisher/test_reusable_workflows.py tests/agent_process/test_delivery_gate_wiring.py -q` passes; commit 2.1 and 2.2 as `chore: remove the v1 quality callee`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py`, and verify both pass

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py remove-reusable-quality`. Verify that it archives the change, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "chore: remove-reusable-quality" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`) and carries the scenario → test map
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`). The removal is pinned by `tests/publisher/test_reusable_workflows.py::test_the_v1_quality_callee_is_gone`. The surviving link-step contract moves to `quality.yml` in `::test_quality_verifies_the_pr_links_its_issue_before_the_driver`
