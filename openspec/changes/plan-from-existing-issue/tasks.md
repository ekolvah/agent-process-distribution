## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py plan-from-existing-issue --planner Claude --implementer Claude` for tracking issue 242. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/plan-from-existing-issue`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_planning_workflow.py` add `test_plan_from_an_existing_issue` (D1): `_group0()` contains `tracking issue <N>` and `the number of the issue the change is planned from`. Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_planning_workflow.py::test_plan_from_an_existing_issue` and verify it fails in its body. Commit as `test(planning): a change planned from an issue carries its number`

## 2. Procedure (D1)

- [x] 2.1 `skills/agent-process/SKILL.md` Group 0: replace "Its text carries `tracking issue <N>`; the propose tail replaces the placeholder, and both scripts read the token there." with "Its text carries `tracking issue <N>`: the number of the issue the change is planned from, else the placeholder, which the propose tail replaces; both scripts read the token there." `.claude/rules/workflow.md`: "The propose run creates the tracking issue of a change and leaves it in `Planned`." becomes "The propose run leaves the tracking issue of a change in `Planned`, creating it when the change has none." Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` passes. Commit as `fix(planning): Group 0 names the source issue's number`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py plan-from-existing-issue`. Verify that it archives the delta into `openspec/specs/planning/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: plan-from-existing-issue" --body-file <report>`. The report names the tracking issue (#242) as a plain reference (never `Closes`) and carries the scenario → test map
- [ ] 4.3 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `planning` / Plan from an existing issue → `tests/publisher/test_planning_workflow.py::test_plan_from_an_existing_issue`; `tests/publisher/test_start_change.py::test_existing_tracking_issue` (unchanged: no create, `Planned` alone)
