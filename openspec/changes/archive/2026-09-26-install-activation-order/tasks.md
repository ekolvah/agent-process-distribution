## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py install-activation-order --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 183. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 no RED: docs-only (`skip_specs`); the script behaviour the step describes is already covered by the "Caller absent" test of `activate_protection`

## 2. Install step 5

- [x] 2.1 In `skills/agent-process/SKILL.md` Install step 5, replace "Once the first PR shows `agent-process / quality`" with the order: once the installation PR shows `agent-process / quality` and the person has merged it, run the command with that PR's number. Leave the rest of the step unchanged. Verify `git diff --stat origin/main` lists only `SKILL.md` and the change directory; commit as `docs(skill): order protection activation after the installation merge`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py install-activation-order`. Verify that it commits the archive (no spec delta: `skip_specs`) and pushes the branch
- [ ] 4.2 Run `gh pr create --title "install-activation-order" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`) and carries the scenario → test map
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- n/a: `skip_specs` — the change has no delta scenario; the enforced order is held by the existing `distribution` scenario "Caller absent".
