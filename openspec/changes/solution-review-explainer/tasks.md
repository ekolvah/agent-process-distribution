## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py solution-review-explainer --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 176. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `test_plan_is_explained_for_solution_review` and `test_delivered_change_is_explained_for_solution_review` to `tests/publisher/test_planning_workflow.py`: each reads its section with `_section` (`Architect review`, `Delivery`) and asserts `plain words`, `final message` and `cannot publish` in it; the first also asserts `what the person decides` and that the sentence follows `Planned`. Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_planning_workflow.py::test_plan_is_explained_for_solution_review tests/publisher/test_planning_workflow.py::test_delivered_change_is_explained_for_solution_review`, verify both RED, commit as `test(process): solution-review explanation is a procedure step (RED)`

## 2. Procedure

- [ ] 2.1 `skills/agent-process/SKILL.md` `## Architect review`: after "The issue must be `Planned` before the plan is ready.", add one sentence — then explain the plan in plain words (what changes, why, what the person decides) as a page linked in the final message, or in that message when the carrier cannot publish one (design: Name the outcome). Verify that test 1.1 `test_plan_is_explained_for_solution_review` is green
- [ ] 2.2 `skills/agent-process/SKILL.md` `## Delivery`: after the "Stop once …" sentence, add one sentence — then explain the delivered change in plain words as a page linked in the final message, or in that message when the carrier cannot publish one. Verify that `test_delivered_change_is_explained_for_solution_review` and `python -m pytest tests/publisher/test_planning_workflow.py -q` are green
- [x] 2.3 No clause outside the shared skill: `v2-5-delete-control-plane` deleted `.agent-process/docs/architecture/agent-process.md` after the plan (design: The shared skill is the only document edited). Verify that `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py -q` is green, commit Group 2 as `feat(process): explain plan and delivery in plain words for solution review`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py solution-review-explainer`. Verify that it applies the `planning` and `implementation` deltas, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "solution-review-explainer" --body-file <report>`. The report references the tracking issue of task 0.1 without `Closes` and carries the scenario → test map
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `planning / Plan ready` → `tests/publisher/test_planning_workflow.py::test_plan_is_explained_for_solution_review`
- `implementation / Run ends` → `tests/publisher/test_planning_workflow.py::test_delivered_change_is_explained_for_solution_review`
