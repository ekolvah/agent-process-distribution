## 0. Delivery start

- [x] 0.1 Run `agent-process start_change documentation-policy --planner Claude --implementer Claude` for tracking issue 314. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/documentation-policy`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py`, add `test_skill_carries_the_documentation_policy`. It checks the `## Documentation` section of `SKILL.md`, which must sit before `## Proposal`, for `CLAUDE.md`, `.claude/rules/`, `paths:`, `ADR`, `Auto-memory` and `one home` (spec *A consumer reads the documentation policy from the skill*)
- [x] 1.2 Run `agent-process check_red "tests/publisher/test_plugin.py::test_skill_carries_the_documentation_policy"`. Verify that it fails in its body on the missing section. Commit as `test(roles): the skill carries the documentation policy`

## 2. Skill text

- [ ] 2.1 In `skills/agent-process/SKILL.md`, add `## Documentation` after `## Claude harness` with the D1 text. Verify that `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py -q` passes. Commit as `feat(skill): carry the documentation policy`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes
- [ ] 3.3 Live check (Principle V): from the worktree, run `claude -p "Invoke the agent-process skill and quote its '## Documentation' section verbatim." --plugin-dir <worktree> --disallowedTools "Read,Grep,Glob,Bash"` (the prompt goes first: `--disallowedTools` takes every following word). Verify that the reply carries the auto-memory line. Record the command and its output in the PR report

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change documentation-policy`. Verify that it archives the delta into `openspec/specs/roles/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "feat: documentation-policy" --body-file <report>`. The report:
  - references the tracking issue plainly (#314), never with `Closes`;
  - carries the scenario → test map and the live check of 3.3;
  - links the consumer follow-up ekolvah/kinozal_scraper#615.
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push.
  - Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`.
  - Answer P2/P3 without resolving.
  - If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding.
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `roles` / A consumer reads the documentation policy from the skill → `tests/publisher/test_plugin.py::test_skill_carries_the_documentation_policy`
