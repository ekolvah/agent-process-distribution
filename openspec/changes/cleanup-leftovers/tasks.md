## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py cleanup-leftovers --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 217. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 no RED: prose, a manifest display name, and a move whose links the existing `tests/agent_process/test_doc_links.py` already resolves (design D1)

## 2. Leftovers

- [x] 2.1 Set `author.name` in `.claude-plugin/plugin.json` and `owner.name` in `.claude-plugin/marketplace.json` to `ekolvah`. Verify `python -m pytest tests/publisher/test_plugin.py -q` passes
- [x] 2.2 In the docstring of `.agent-process/scripts/navigation_policy.py` (lines 281-283), rewrite the revision condition per design D2: if the refusals fire and context growth before the first edit does not fall, tighten the threshold or revert the rule. Delete the placeholder bullet `AGENTS.md:29-31`. Verify `python -m pytest tests/agent_process/test_navigation_policy.py -q` passes; commit 2.1 and 2.2 as `chore: remove origin-project leftovers`

## 3. Move the telemetry document

- [x] 3.1 `git mv docs/telemetry-measurement-setup.md .agent-process/docs/telemetry-measurement-setup.md`. In it, change `../.agent-process/docs/adr/0029-…` and `../.agent-process/docs/adr/0026-…` to `adr/0029-…` and `adr/0026-…`. In `.agent-process/docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md:189`, change `../../../docs/telemetry-measurement-setup.md` to `../telemetry-measurement-setup.md`. Verify `docs/` no longer exists and `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_adr_records.py -q` passes; commit as `docs: move the telemetry setup under .agent-process/docs`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py`, and verify that both pass

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py cleanup-leftovers`. Verify that it archives the change, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "chore: cleanup-leftovers" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`) and carries the scenario → test map
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`). The move is pinned by the existing `tests/agent_process/test_doc_links.py`; the text edits have no test (design D1)
