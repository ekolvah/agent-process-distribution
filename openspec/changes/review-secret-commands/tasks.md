## 0. Delivery start

- [x] 0.1 Run `agent-process start_change review-secret-commands --planner Claude --implementer Claude` for tracking issue 288. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/review-secret-commands`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed`, add assertions that the row contains `claude setup-token` and `f"gh secret set CLAUDE_CODE_OAUTH_TOKEN -R {CONSUMER}"`; keep the secrets-page URL, one-row and no-secret-write assertions
- [x] 1.2 Run `agent-process check_red "tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed"` and verify both parametrizations fail on the new assertions. Commit as `test(distribution): review-secret row gives the token commands`

## 2. Row and Install step

- [ ] 2.1 `skills/agent-process/scripts/manual.py` (D1): the `review-secret` row reads `manual review-secret: https://github.com/{t.repo}/settings/secrets/actions -- claude setup-token, then gh secret set {REVIEW_TOKEN} -R {t.repo} and paste the token at its prompt; the review caller passes it to the review`. Verify `python -m pytest tests/publisher/test_init_remote.py -q` passes (including the `secret-403` case)
- [ ] 2.2 `skills/agent-process/SKILL.md` Install step 3 (D2): the person runs `claude setup-token`, then `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` and pastes the token at its prompt, so the token never enters the chat; the rest of the step is unchanged. Verify `python -m pytest tests/publisher/test_planning_workflow.py tests/publisher/test_plugin.py -q` passes. Commit 2.1–2.2 as `fix(distribution): review-secret row gives the token commands`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change review-secret-commands`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: review-secret-commands" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#288), carries the scenario → test map and the observation of proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Review prerequisites → `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed`
