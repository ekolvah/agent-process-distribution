## 0. Delivery start

- [x] 0.1 Run `agent-process start_change upstream-consumer-principles --planner Claude --implementer Claude` for tracking issue 316. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/upstream-consumer-principles`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 no RED: docs-only (`skip_specs`), principle prose under the `principles.md` §I documentation exception

## 2. Upstreamed principles

- [x] 2.1 In `skills/agent-process/principles.md`, apply the D2 wording: the §V evidence sentences and mitigation example, the two Quality Gates bullets. Verify that `grep -n "not enforced" skills/agent-process/principles.md` prints nothing and `python -m pytest tests/publisher tests/agent_process -q` passes. Commit as `docs(principles): upstream consumer evidence bounds, gates and conventions`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change upstream-consumer-principles`. Verify that it archives the change with no spec update, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "docs: upstream-consumer-principles" --body-file <report>`. The report references the tracking issue plainly (#316), never with `Closes`, names the principles the change interacts with (§V, Quality Gates; MINOR), and carries the scenario → test map and the consumer-side follow-up
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`): the change edits principle prose only.
