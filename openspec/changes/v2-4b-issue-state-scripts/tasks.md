## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-4b-issue-state-scripts --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 174. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 no RED: the change deletes unused scripts, and the one modified requirement is realigned to behaviour that `start_change` already has (design D3). Verify that `python -m pytest "tests/publisher/test_delivery_scripts.py::test_interrupted_start_names_the_continuation" -q` is green

## 2. Delete the v1 scripts

- [x] 2.1 Delete `.agent-process/scripts/issue_branch.py`, `new_branch.py`, `set_issue_status.py`, `set_issue_priority.py`, `project_settings.py` and `tests/agent_process/test_issue_branch.py` (design D1). Verify that `python -m pytest tests -q` is green
- [x] 2.2 Delete `.agent-process/scripts/open_pr.py`, `update_pr_body.py`, `check_orphan_scope.py` and `tests/publisher/test_deferred_scope.py` (design D2). Verify that `python -m pytest tests -q` is green, then commit Group 2 as `refactor(state): delete the v1 issue and state scripts`

## 3. Prose

- [x] 3.1 Apply design D4:
  - `.agent-process/docs/architecture/agent-process.md`: delivery steps 3 and 4, the `## Out of scope` paragraph, and governance item 5;
  - `AGENTS.md` and `.claude/rules/workflow.md`: the activation sentences;
  - the `skills/agent-process/scripts/set_status.py` docstring;
  - one ADR 0027 Observations bullet after the `v2-4a` bullet.

  Verify that `git grep -n -E "issue_branch|new_branch|open_pr|update_pr_body|check_orphan_scope|set_issue_status|set_issue_priority|project_settings" -- ':!openspec/changes' ':!**/adr/**' ':!.agent-process/docs/architecture/agent-process-installation.md'` prints nothing, and that `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py -q` is green. Commit as `docs(state): drop the v1 issue and state scripts from the process docs`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py v2-4b-issue-state-scripts`. Verify that it applies the `state` delta, commits the archive, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "v2-4b-issue-state-scripts" --body-file <report>`. The report references the tracking issue of task 0.1 and issue 114 without `Closes`. It carries the scenario → test map, and it names issue 115 as the owner of the retired installation guide and the PR template
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, report the PR ready. The person merges it

## Scenario → test map

- `state / Board failure` → `tests/publisher/test_delivery_scripts.py::test_interrupted_start_names_the_continuation`
