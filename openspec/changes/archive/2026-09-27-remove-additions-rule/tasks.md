## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py remove-additions-rule --planner Claude --implementer Claude` for tracking issue 186. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 In `tests/publisher/test_start_change.py` drop `"additions": []` from `_review`, remove `_addition`, and add `test_plan_without_a_prior_issue`: an `approve` review with every class `ok` and no `additions` key makes `create_tracking_issue.main([_CHANGE, "--area", "Observability"])` create exactly one issue. Rewrite `test_addition_without_evidence` whole, its `approve`-with-reference and `rework` tails included: the review with `"additions": []` added exits 2 from both `create_tracking_issue` and `start_change`, creates nothing, and stderr contains `Additional properties are not allowed ('additions'`. In `tests/publisher/test_planning_workflow.py` drop `"additions": []` from its review fixture and make `test_over_long_rule_or_bespoke_check` assert that the `bespoke` description contains `script or check the plan adds`, `design.md decision`, `closes` and `does not fit` and not `non-test file`, that `additions` is not a schema property, and that `_section("Design")` contains `the problem it closes` and `the standard for its job`. Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_start_change.py::test_plan_without_a_prior_issue tests/publisher/test_start_change.py::test_addition_without_evidence tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check`; verify each fails in the test body; commit as `test(planning): review validates without additions`

## 2. Schema and procedure (D1–D4)

- [x] 2.1 Per D1 remove `additions` from `required`, from the `then` block and from `properties` of `skills/agent-process/architect-review.schema.json`; per D2 replace the `bespoke` description. Verify `python -m pytest tests/publisher/test_start_change.py tests/publisher/test_planning_workflow.py -q` fails only on the Design assertion
- [x] 2.2 Per D3 add the bullet to `## Design` of `skills/agent-process/SKILL.md`; per D4 add the bullet after the issue 170 entry of `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`. Verify `python -m pytest tests/publisher/test_start_change.py tests/publisher/test_planning_workflow.py -q` passes; commit as `feat(planning): bespoke justification lives in design.md`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes (all checks pass after rebase on the fix of issue 231; before it `secrets` exited with WinError 206 on Windows)

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py remove-additions-rule`. Verify that it archives the delta into `openspec/specs/`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "feat: remove-additions-rule" --body-file <report>`. The report names tracking issue 186 as a plain reference (never `Closes`), carries the scenario → test map, marks the removed `additions` key as breaking, and states the consumer migration of design.md
- [ ] 4.3 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `planning` / Plan without a prior issue → `tests/publisher/test_start_change.py::test_plan_without_a_prior_issue`
- `planning` / Addition without evidence → `tests/publisher/test_start_change.py::test_addition_without_evidence`
- `planning` / Over-long rule or bespoke check → `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check`
- `planning` / Review class without evidence → unchanged; `tests/publisher/test_start_change.py::test_review_not_valid`
- `planning` / Rework verdict → unchanged; `tests/publisher/test_start_change.py::test_verdict_is_rework`
- `planning` / Review finding → unchanged; `tests/publisher/test_planning_workflow.py::test_review_finding`
- `planning` / Plan approved → unchanged; `tests/publisher/test_planning_workflow.py::test_plan_approved`, `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue`
- `planning` / Existing tracking issue → unchanged; `tests/publisher/test_start_change.py::test_existing_tracking_issue`
- `planning` / Review archives with the change → unchanged; `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change`
