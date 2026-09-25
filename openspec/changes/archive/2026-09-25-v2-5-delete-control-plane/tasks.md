## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-5-delete-control-plane --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 115. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 Add `test_workflows_stay_within_the_size_budget` to `tests/publisher/test_reusable_workflows.py`: for every file under `.github/workflows/`, fail and name each one over 150 lines (design D4). no RED: the budget holds on `main` (largest workflow 125 lines), so the test is born green; show its failing branch once by appending 30 comment lines to `.github/workflows/reusable-agent-review.yml`, running `python -m pytest "tests/publisher/test_reusable_workflows.py::test_workflows_stay_within_the_size_budget" -q` (verify it fails and names `reusable-agent-review.yml`), then `git checkout -- .github/workflows/reusable-agent-review.yml` and re-run it green. Commit as `test(maintenance): workflow size budget`

## 2. Delete the control plane and its orphans

- [x] 2.1 Delete `.agent-process/scripts/agent_orchestrator.py`, `.agents/orchestration/roles.yaml`, `.agents/orchestration/state.example.json` and `tests/agent_process/test_agent_orchestrator.py` (design D1). Verify that `python -m pytest tests -q` is green
- [x] 2.2 Delete `.agent-process/scripts/check_review_credentials.py`, `tests/agent_process/test_review_credentials.py`, `.github/pull_request_template.md`, and `test_installation_documents_the_caller_workflow_trust_boundary` in `tests/publisher/test_reusable_workflows.py` (design D2). Verify that `python -m pytest tests -q` is green, then commit Group 2 as `refactor(maintenance): delete the v1 control plane`

## 3. Documents

- [x] 3.1 Delete `.agent-process/docs/architecture/agent-process.md` and `.agent-process/docs/architecture/agent-process-installation.md`, and retarget every pointer as design D2 lists: `AGENTS.md` (source-of-truth sentence, delivery-flow link, the advisory-control-plane bullet removed, one line for `check_codex_project_trust.py` in the Codex adapter section per D3), `.claude/rules/workflow.md`, `.claude/rules/mindset.md`, `.claude/rules/testing.md`, the v1 sentence of `openspec/config.yaml` `context`, the header, the six links and §Governance of `principles.md`, the `pip-compile` message of `.agent-process/scripts/hooks.py`, and one link each in ADR 0003, 0004 and 0009. Verify that `git ls-files .agent-process/docs/architecture` prints only `principles.md`; that `git grep -n -E "agent-process(-installation)?\.md|agent_orchestrator|roles\.yaml|state\.example|check_review_credentials|pull_request_template" -- ':!openspec/changes' ':!**/adr/**'` prints only the historical comment of `.agent-process/scripts/navigation_policy.py` (design Non-Goals); that `git grep -n -E "docs/architecture/?\)|architecture/\*|other architecture docs|enforced process is v1" -- ':!openspec/changes' ':!**/adr/**'` prints nothing; and that `python -m pytest tests/agent_process/test_doc_links.py tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_narrative.py tests/agent_process/test_adr_records.py -q` is green
- [x] 3.2 Append to ADR 0027 one `Observations from v2-5` block (design D5): the `codex features list` output of D3 and the open rest of that deletion condition; the size-budget answer of D4; the telemetry comparison of review rounds moved to step 6 (issue 116). Verify that `python -m pytest tests/agent_process/test_adr_records.py tests/agent_process/test_doc_narrative.py -q` is green, then commit Group 3 as `docs(maintenance): drop the v1 process documents`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory, and that `git diff --shortstat origin/main` shows more deletions than insertions

## 5. Deliver

- [x] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py v2-5-delete-control-plane`. Verify that it applies the `maintenance` delta, commits the archive, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "v2-5-delete-control-plane" --body-file <report>`. The report references tracking issue 115 and issue 107 without `Closes`, carries the scenario → test map, and names the open rest of the Codex deletion condition (design D3)
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. A fix that changes a spec goes through a change of its own on the PR branch; a changed design decision amends the archived `design.md` and this map in the same push. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, report the PR ready. The person merges it

## Scenario → test map

- `maintenance / Workflow over the budget` → `tests/publisher/test_reusable_workflows.py::test_workflows_stay_within_the_size_budget`
