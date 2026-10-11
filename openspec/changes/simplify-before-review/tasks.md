## 0. Delivery start

- [x] 0.1 Run `agent-process start_change simplify-before-review --planner Claude --implementer Claude` for tracking issue 387. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/simplify-before-review`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add to `tests/publisher/test_planning_workflow.py`, with its `_skill()` and `_section()` helpers:
  - `test_simplify_precedes_the_architect_review`: in `_section("Architect review")`, `/simplify openspec/changes/<change>/` comes before `architect-reviewer`, with `once` and `what `/simplify` changed`
  - `test_simplify_opens_verify`: in the `## Tasks` slice between ` 4. Verify` and ` 5. `, the literal phrase ``/simplify` without an argument` comes before `openspec validate`

  Run `agent-process check_red tests/publisher/test_planning_workflow.py::test_simplify_precedes_the_architect_review tests/publisher/test_planning_workflow.py::test_simplify_opens_verify` and commit RED with the Group 1 ticks

## 2. Skill text (design D2, D3)

- [x] 2.1 In `skills/agent-process/SKILL.md`, extend the first sentence of `## Architect review`: after `tasks.md`, run `/simplify openspec/changes/<change>/` once, then review. Add to the plain-words explanation in that section: what `/simplify` changed. Open `## Tasks` item 4 Verify with `/simplify` without an argument, its edits committed. Keep the item numbers. Verify with `python -m pytest tests/publisher/test_planning_workflow.py`. Commit

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument, and commit its edits or record `no edits` with the skipped findings in this tick
- [ ] 3.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change simplify-before-review`. Verify that it merges the deltas into `openspec/specs/planning/spec.md` and `openspec/specs/implementation/spec.md`, archives, commits and pushes the branch
- [ ] 4.2 Run `gh pr create --title "feat: simplify-before-review" --body-file <report>`. The report references tracking issue #387 plainly, never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change. The person merges it

## Scenario → test map

| Scenario | Test |
|---|---|
| Plan written (`planning`) | `tests/publisher/test_planning_workflow.py::test_simplify_precedes_the_architect_review` |
| Implementation done (`implementation`) | `tests/publisher/test_planning_workflow.py::test_simplify_opens_verify` |
