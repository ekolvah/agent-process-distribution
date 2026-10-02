## 0. Delivery start

- [x] 0.1 Run `agent-process start_change delete-check-imports --planner Claude --implementer Claude` for tracking issue 326. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/delete-check-imports`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [ ] 1.1 no RED: deletion of a function no check registers and nothing calls; the check set it could change is the `--list` output, unchanged (proposal Why)

## 2. Delete

- [ ] 2.1 In `.agent-process/scripts/ci_check.py`, record `python .agent-process/scripts/ci_check.py --list`, then delete `check_imports` with its two following blank lines, and in the comment of `_secrets_cmd` drop only the clause ", same reason as check_imports" (the `--baseline` sentence stays). Verify that `git grep -n "check_imports\|importlinter\|lint-imports" -- . ':!openspec/changes'` prints nothing, that `--list` prints the same checks as recorded before the edit, and that `python -m pytest tests/agent_process/test_ci_check.py -q` passes. Commit as `refactor(implementation): delete the unregistered check_imports`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change delete-check-imports`. Verify that it archives the change, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "refactor: delete-check-imports" --body-file <report>`. The report references the tracking issue plainly (#326), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`). The unchanged check set is shown by `ci_check.py --list` before and after the edit in 2.1; nothing to pin with a test
