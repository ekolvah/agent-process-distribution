## 0. Start the delivery

- [x] 0.1 Run `python .agent-process/scripts/start_change.py v2-2-delivery --planner Codex --implementer Codex` for tracking issue 112; do not create the implementation branch until this planned change and its approved architect review are present.

## 1. Prove the target behavior RED

- [x] 1.1 Add `tests/publisher/test_plugin.py` coverage for the shared skill, pointer-only OpenSpec rules, no hooks, the closed consumer footprint, publisher dogfooding, and one `2.0.0` version identity. Run the selected nodes and prove them RED with `python .agent-process/scripts/check_red.py <node-ids>`.
- [x] 1.2 Add `tests/publisher/test_init.py` with temporary repositories, homes, and a fake UTF-8 subprocess runner. Cover fresh install, repeat install, consumer-file conflicts, dry-run/confirmation, literal multiline setup/test commands, the Codex checkout and link on Windows and Unix, ruleset create/update/ambiguity, Project copy/link/reuse/ambiguity, and the printed secret/Codex/Project instructions. Prove the selected nodes RED with `python .agent-process/scripts/check_red.py <node-ids>`.
- [x] 1.3 Rewrite `tests/publisher/test_reusable_workflows.py` around one caller: caller-declared setup/test inputs, pinned reusable quality on the PR head, issue-link and strict OpenSpec steps, non-zero consumer commands, the direct Claude action, advisory review, Dependabot, and a ruleset that requires only `quality / quality`. Prove the selected nodes RED with `python .agent-process/scripts/check_red.py <node-ids>`.
- [x] 1.4 Update the planning, delivery, CI, documentation, and path-contract tests for skill-owned scripts, no copied procedure/report-path contract, and removal of Copier attribution. Prove every newly behavioral selected node RED with `python .agent-process/scripts/check_red.py <node-ids>`; record any Principle I exemption beside a rename-only expectation.
- [x] 1.5 Commit the RED tests before implementation.

## 2. Build the shared plugin procedure

- [x] 2.1 Move `archive_change.py`, `check_red.py`, `create_tracking_issue.py`, `resolve_review_thread.py`, `set_status.py`, `start_change.py`, and `wait_for_pr.py` into `skills/agent-process/scripts/`; update their standalone usage text and repository tests without introducing imports from `.agent-process`. Verify `python -m pytest tests/publisher/test_delivery_scripts.py tests/publisher/test_resolve_review_thread.py -q`.
- [x] 2.2 Add `skills/agent-process/SKILL.md` with the proposal, tasks, architect-review, and install sections. Replace copied artifact rules in `openspec/config.yaml` with short section pointers while preserving this repository's context. Verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py -q -k "rule_change or planning"`.
- [x] 2.3 Add the thin Claude `init` command, expose the shared skill in the plugin, remove every distributed hook declaration/payload, and set the plugin and marketplace manifests to `2.0.0`. Verify `python -m pytest tests/publisher/test_plugin.py -q -k "no_hooks or version"`.
- [x] 2.4 Keep only the two portable plugin-enablement keys in the settings template while preserving this publisher's repository-specific settings. Remove `copier-answers.yml` and its source-attribution contract. Verify `python -m pytest tests/publisher/test_plugin.py tests/agent_process/test_delivery_gate_wiring.py -q -k "settings or attribution"`.
- [x] 2.5 Run the Group 1 plugin, planning, delivery, and path-contract tests GREEN, then commit the shared-procedure unit.

## 3. Implement deterministic initialization

- [x] 3.1 Add only the five owned templates: `agent-process.yml`, `dependabot.yml`, `config.yaml`, `settings.json`, and `ruleset.json`. Make workflow substitution YAML-safe for literal multiline setup/test commands. Verify `python -m pytest tests/publisher/test_plugin.py::test_closed_installed_payload tests/publisher/test_init.py -q -k "literal_commands"`.
- [x] 3.2 Implement the stdlib-only local `init.py` seam and dry-run/confirmation state machine with UTF-8 subprocess capture and unmodified `None` stdout/stderr. Verify `python -m pytest tests/publisher/test_init.py -q -k "dry_run or confirmation or utf8 or none_capture"`.
- [x] 3.3 Implement pinned OpenSpec initialization, the marker-owned config pointer, owned caller, conflict-safe Dependabot entry, and two-key Claude settings merge. Verify `python -m pytest tests/publisher/test_init.py::test_fresh_repository tests/publisher/test_init.py::test_second_run tests/publisher/test_init.py::test_consumer_owned_file -q`.
- [x] 3.4 Implement the versioned Codex checkout plus `~/.agents/skills/agent-process` symlink or Windows junction. Refuse dirty checkouts, foreign links, and destructive replacement before fetching and selecting the requested tag. Verify `python -m pytest tests/publisher/test_init.py -q -k "codex_checkout or skill_link"`.
- [x] 3.5 Implement unique-name ruleset create/update/read-back and fail on several name matches. Verify `python -m pytest tests/publisher/test_init.py::test_ruleset_blocks_direct_updates tests/publisher/test_init.py::test_ruleset_requires_quality tests/publisher/test_init.py -q -k "ruleset"`.
- [x] 3.6 Implement zero/one/many linked-Project handling with `gh project copy 4` and `gh project link`; do not verify fields or workflow switches. Verify `python -m pytest tests/publisher/test_init.py -q -k "project"`.
- [x] 3.7 Print, but do not execute, the secret command, Codex automatic-review instruction, and Project visibility/workflow checklist. Verify `python -m pytest tests/publisher/test_init.py -q -k "printed_instructions"`.
- [x] 3.8 Exercise `init --dry-run` against a temporary fixture repository; verify no write occurs, then use the fake-remote seam for a confirmed run and assert no repository file outside the closed allow-list. Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_plugin.py::test_closed_installed_payload -q`.
- [x] 3.9 Commit the initialization unit.

## 4. Replace the workflow and review surface

- [x] 4.1 Extend `reusable-quality.yml` with setup/test inputs, linked-issue validation, PR-head checkout, optional setup, the consumer test command, and pinned strict OpenSpec validation when `openspec/` exists. Verify `python -m pytest tests/publisher/test_reusable_workflows.py::test_quality_check_on_a_pr tests/publisher/test_reusable_workflows.py::test_consumer_test_failure_is_quality_failure -q`.
- [x] 4.2 Add the single publisher `.github/workflows/agent-process.yml` caller using `@main` until the release tag exists. Pass the publisher dependency install and `ci_check.py` as setup/test. Verify `python -m pytest tests/publisher/test_reusable_workflows.py -q -k "one_caller or publisher"`.
- [x] 4.3 Invoke `anthropics/claude-code-action@v1` directly in an advisory job, with no custom parser, fallback, required verdict, or process-owned Codex request. Verify `python -m pytest tests/publisher/test_reusable_workflows.py::test_direct_advisory_reviews tests/publisher/test_reusable_workflows.py::test_review_is_visible_but_not_required -q`.
- [x] 4.4 Delete `ci.yml`, `agent-review.yml`, and `reusable-agent-review.yml`, and add the GitHub Actions Dependabot entry. Verify `python -m pytest tests/publisher/test_reusable_workflows.py tests/publisher/test_plugin.py::test_version_drift -q`.
- [x] 4.5 Add the active, no-bypass default-branch ruleset template requiring pull requests, strict `quality / quality` from GitHub Actions integration `15368`, non-fast-forward protection, and deletion protection. Verify `python -m pytest tests/publisher/test_init.py::test_ruleset_blocks_direct_updates tests/publisher/test_init.py::test_ruleset_requires_quality -q`.
- [x] 4.6 Run the Group 1 workflow, ruleset, version, and CI-contract tests GREEN, then commit the workflow/review unit.

## 5. Record the new operational boundary

- [x] 5.1 Update `AGENTS.md`, `.claude/rules/`, the canonical process document, and every executable path example to load the shared skill and call its moved scripts. Keep this implementation run's transitional delivery commands explicit until the new process is merged. Verify `python -m pytest tests/publisher/test_planning_workflow.py tests/publisher/test_delivery_scripts.py tests/agent_process/test_doc_links.py -q`.
- [x] 5.2 Amend ADR 0027 with the observed OpenSpec bootstrap, current Codex skill/link location, one-caller/direct-action choice, Project copy/link boundary, name-bound required-check limitation, dropped-hook/review proofs, and current-head workflow-diff merge boundary. Verify `python -m pytest tests/agent_process/test_adr_records.py tests/agent_process/test_doc_narrative.py -q`.
- [x] 5.3 Update the installation document with the exact installed allow-list, bootstrap/update/rollback steps, advisory review behavior, and the person-owned secret/Codex/Project UI actions. Do not add a consumer `AGENTS.md` fragment, report-path convention, copied process test, or field/workflow verifier. Verify `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py tests/agent_process/test_doc_narrative.py tests/publisher/test_plugin.py -q`.
- [x] 5.4 Run the documentation and source-of-truth tests GREEN, then commit the documentation/contract unit.

## 6. Verify the implementation

- [x] 6.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all`.
- [x] 6.2 Run `python .agent-process/scripts/ci_check.py` using the publisher's retained v1 entry point and fix failures at their root without widening the change.
- [x] 6.3 Review `git diff`, confirm the implementation matches the closed footprint and explicit proof losses, check `git status --short`, and commit any final implementation-only correction.

## 7. Transition the live protection with the person

- [x] 7.1 Stop for explicit person confirmation of the live transition. Then install the issue-112 ruleset and read back that it is active, targets the default branch, has no bypass actor, and requires strict `quality / quality` from integration `15368`.
- [x] 7.2 Remove only `agent-review / agent-review` from classic protection. Read back that classic strict `quality / quality`, the repository's other classic protections, and the active ruleset all remain; restore the old review context before reverting the caller if rollback is needed.

## 8. Archive, publish, and inspect the final head

- [x] 8.1 Verify a clean worktree, then run `python skills/agent-process/scripts/archive_change.py v2-2-delivery`.
- [x] 8.2 Run `gh pr create --title "v2-2-delivery" --body-file <report>` with issue 112 as a plain reference (no `Closes`), the archived design, the scenario-to-test map, the accepted trust-boundary gaps, and the protection-transition evidence. If an interrupted run finds the change archived, resume from `gh pr view v2-2-delivery` instead of re-entering apply.
- [ ] 8.3 For this transitional issue only, run `python .agent-process/scripts/request_codex_review.py --request <PR>` under the currently enforced v1 process, then run `python skills/agent-process/scripts/wait_for_pr.py <PR>` until all checks on one settled head conclude.
- [ ] 8.4 Address or answer findings in at most three rounds. After every push, re-run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`. Resolve an addressed older-head P0/P1 thread only with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>` from the fixing session; answer P2/P3 without resolving. A spec fix uses its own delta and archive, and an archived-design change updates the archived design and scenario map in the same push.
- [ ] 8.5 On the settled current head, run `gh pr diff <PR> --name-only`, inspect every `.github/workflows/**` diff and the visible advisory review state, and hand the PR to the person without merging it. After human merge, create the immutable `v2.0.0` tag from the default branch.

## Scenario → test map

| Capability | Scenario | Test evidence |
|---|---|---|
| distribution | Fresh repository | `tests/publisher/test_init.py::test_fresh_repository` |
| distribution | Second run | `tests/publisher/test_init.py::test_second_run` |
| distribution | Consumer-owned file | `tests/publisher/test_init.py::test_consumer_owned_file` |
| distribution | Rule change | `tests/publisher/test_plugin.py::test_rule_change` |
| distribution | New release | `tests/publisher/test_plugin.py::test_version_drift` |
| distribution | Quality check on a PR | `tests/publisher/test_reusable_workflows.py::test_consumer_caller_pins_release_tag` |
| distribution | Quality check on the publisher PR | `tests/publisher/test_reusable_workflows.py::test_publisher_caller_uses_local_reusable` |
| distribution | Rendered payload | `tests/publisher/test_plugin.py::test_closed_installed_payload` |
| distribution | Process change | `tests/publisher/test_plugin.py::test_publisher_dogfoods_process` |
| implementation | Consumer test fails | `tests/publisher/test_reusable_workflows.py::test_consumer_test_failure_is_quality_failure` |
| implementation | Behavioural change | `tests/publisher/test_delivery_scripts.py::test_behavioural_change` |
| implementation | Runner given | `tests/publisher/test_delivery_scripts.py::test_runner_owns_the_selection` |
| implementation | Configuration that cuts the run | `tests/publisher/test_delivery_scripts.py::test_interrupted_run_is_no_verdict` |
| implementation | Pending review | `tests/publisher/test_delivery_scripts.py::test_pending_review` |
| implementation | Empty rollup after a push | `tests/publisher/test_delivery_scripts.py::test_empty_rollup_after_push` |
| implementation | Tasks of a new change | `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` |
| implementation | Propose run stopped before its tail | `tests/publisher/test_delivery_scripts.py::test_propose_run_stopped_before_its_tail` |
| implementation | Verdict is rework | `tests/publisher/test_delivery_scripts.py::test_verdict_is_rework` |
| implementation | Blocking thread addressed | `tests/publisher/test_resolve_review_thread.py::test_close_round_resolves_and_replies_without_rerunning_the_head` |
| implementation | Review fix changes a spec | `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` |
| implementation | Design decision changed at review | `tests/publisher/test_planning_workflow.py::test_design_decision_changed_at_review` |
| implementation | Finding closed by its class | `tests/publisher/test_planning_workflow.py::test_finding_closed_by_its_class` |
| review-and-merge | Direct default-branch update | `tests/publisher/test_init.py::test_ruleset_blocks_direct_updates` |
| review-and-merge | Pull request review | `tests/publisher/test_reusable_workflows.py::test_direct_advisory_reviews` |
| review-and-merge | Review unavailable | `tests/publisher/test_reusable_workflows.py::test_review_is_visible_but_not_required` |
| review-and-merge | Missing required context | `tests/publisher/test_init.py::test_ruleset_requires_quality` |
| maintenance | Version drift | `tests/publisher/test_plugin.py::test_version_drift` |
