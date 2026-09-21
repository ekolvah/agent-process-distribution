## 0. Delivery start

- [x] 0.1 Run `python .agent-process/scripts/start_change.py v2-2g-a-package-foundation --planner Codex --implementer Codex` for tracking issue 152; verify it reads this approved review, creates the linked branch from `origin/main`, moves #152 from Planned to In Progress, and posts the provenance comment before any RED or implementation work

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_plugin.py` with `test_shared_skill_owns_the_procedure_and_scripts`, `test_package_has_no_installer_state`, `test_publisher_dogfoods_process`, and `test_version_drift`; update `tests/publisher/test_planning_workflow.py` with `test_artifact_rules_point_to_shared_skill` and preserved procedure assertions; update `tests/publisher/test_delivery_scripts.py` with `test_moved_start_scripts_resolve_consumer_root`, moved sibling/recovery-command expectations, and an exact seven-script boundary; make `tests/publisher/test_resolve_review_thread.py` load the moved source without changing its behavioral assertions; verify `python .agent-process/scripts/check_red.py tests/publisher/test_plugin.py::test_shared_skill_owns_the_procedure_and_scripts tests/publisher/test_plugin.py::test_package_has_no_installer_state tests/publisher/test_plugin.py::test_publisher_dogfoods_process tests/publisher/test_plugin.py::test_version_drift tests/publisher/test_planning_workflow.py::test_artifact_rules_point_to_shared_skill tests/publisher/test_delivery_scripts.py::test_moved_start_scripts_resolve_consumer_root` exits 0 with every named new case RED; commit as `test(distribution): RED for the shared package boundary`

## 2. Shared skill and portable script boundary

- [ ] 2.1 Add `skills/agent-process/SKILL.md` by moving the current proposal/specification/design/tasks/architect-review/delivery procedure without changing its current Codex request, fallback review, thread resolution, rerun, review-gate, or three-round behavior; verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py -q -k "shared_skill or artifact_rules or tasks_of_a_new_change or review"` is green for the shared-source assertions
- [ ] 2.2 Move exactly `archive_change.py`, `check_red.py`, `create_tracking_issue.py`, `resolve_review_thread.py`, `set_status.py`, `start_change.py`, and `wait_for_pr.py` into `skills/agent-process/scripts/`; resolve sibling imports and emitted continuation commands from that directory and repository operations from invocation `cwd`; verify `python -m pytest tests/publisher/test_delivery_scripts.py tests/publisher/test_resolve_review_thread.py -q` is green, including consumer-root and current thread/rerun behavior
- [ ] 2.3 Verify the package contains no `init.py`, templates, hook payload, workflow replacement, ruleset/protection payload, or remaining control-plane script with `tests/publisher/test_plugin.py::test_package_has_no_installer_state`; commit Group 2 as `feat(distribution): establish the shared skill package`

## 3. Rule pointers and publisher dogfood

- [ ] 3.1 Replace the long proposal/specification/design/tasks rule bodies in `openspec/config.yaml` with one short pointer per artifact to the matching shared-skill section while retaining schema and repository context; point `agents/architect-reviewer.md`, `AGENTS.md`, `.claude/rules/testing.md`, `.claude/rules/workflow.md`, and `.agent-process/docs/architecture/agent-process.md` at the shared contract and moved paths; verify `python -m pytest tests/publisher/test_planning_workflow.py tests/agent_process/test_doc_links.py tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_narrative.py -q` is green
- [ ] 3.2 Set `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` to the same `2.0.0` identity and merge only the local marketplace/plugin activation keys into this publisher's `.claude/settings.json`, preserving telemetry, permissions, and v1 hooks; verify `python -m pytest tests/publisher/test_plugin.py -q -k "version_drift or publisher_dogfoods"` is green and no release tag or consumer reference is created
- [ ] 3.3 Run `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py tests/publisher/test_delivery_scripts.py tests/publisher/test_resolve_review_thread.py -q` to prove the two delta scenarios and package boundary together; commit Group 3 as `feat(distribution): dogfood the shared package source`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify every change and spec passes
- [ ] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify the complete repository quality suite passes under the unchanged v1 workflows, hooks, review policy, and protection; confirm `git diff --name-only` contains no installer, template, workflow, Project, ruleset/protection, or unrelated control-plane file

## 5. Deliver

- [ ] 5.1 Verify `git status --short` is empty after committing all implementation work, then run `python skills/agent-process/scripts/archive_change.py v2-2g-a-package-foundation`; verify it applies the `roles` and `distribution` deltas, archives the reviewed plan, commits it, and pushes the linked issue branch
- [ ] 5.2 Create the PR with `gh pr create --title "v2-2g-a-package-foundation" --body-file <report>`; the report references #152 without `Closes`, includes the scenario → test map, and names #155/#156/#153/#154/#114/#115 as excluded ownership
- [ ] 5.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`; for each corrective push rerun both, then use `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>` only for an addressed older-head P0/P1 thread, answer but do not resolve P2/P3, and run `python .agent-process/scripts/review_gate.py <PR>` on the settled current head; stop only at `ready-for-human` or the documented three-round escalation, and leave post-archive tasks unticked in git

## Scenario → test map

- `roles / Procedure changes once` → `tests/publisher/test_plugin.py::test_shared_skill_owns_the_procedure_and_scripts` and `tests/publisher/test_planning_workflow.py::test_artifact_rules_point_to_shared_skill`
- `distribution / Process change` → `tests/publisher/test_plugin.py::test_publisher_dogfoods_process`
