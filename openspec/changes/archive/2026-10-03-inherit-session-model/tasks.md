## 0. Delivery start

- [x] 0.1 Run `agent-process start_change inherit-session-model --planner Claude --implementer Claude` for tracking issue 317. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/inherit-session-model`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py`, add `test_plugin_agents_inherit_the_session_model`: for every `agents/*.md`, parse the YAML between the leading `---` lines and assert `model == "inherit"` and no `effort` key; assert at least one agent was read
- [x] 1.2 Run `agent-process check_red "tests/publisher/test_plugin.py::test_plugin_agents_inherit_the_session_model"`. Verify that it fails in its body on `claude-opus-5`. Commit as `test(roles): plugin agents inherit the session model`

## 2. Agent frontmatter

- [x] 2.1 In `agents/architect-reviewer.md`, replace `model: claude-opus-5` with `model: inherit` and remove `effort: high` (design D1, D2). Verify that `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py -q` passes. Commit as `fix(roles): architect-reviewer inherits the session model`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `agent-process archive_change inherit-session-model`. Verify that it archives the delta into `openspec/specs/roles/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: inherit-session-model" --body-file <report>`. The report references the tracking issue plainly (#317), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `roles` / Agent frontmatter read → `tests/publisher/test_plugin.py::test_plugin_agents_inherit_the_session_model`
