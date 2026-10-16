## 0. Delivery start

- [x] 0.1 Run `agent-process start_change principles-one-home --planner Claude --implementer Claude` (tracking issue 443), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 Apply design decision 6 to `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` and `::test_package_contents_are_closed`, and to `tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle`
- [ ] 1.2 Run `agent-process check_red` with the three node ids of 1.1 and commit RED with these ticks

## 2. One home

- [ ] 2.1 Delete `skills/agent-process/principles.md` (design decision 5) (spec roles: The skill carries the principles core and harness tactics); apply decision 6 to `tests/agent_process/test_doc_headers.py` (spec maintenance: Documents are guarded) and to the coupling test in `tests/publisher/test_reusable_workflows.py` (spec review-and-merge: Reviewer instructions name the simplicity triggers); verify `tests/agent_process/test_doc_headers.py`, `tests/agent_process/test_issue_refs.py` and `tests/publisher/test_reusable_workflows.py::test_review_contract_names_the_narrow_simplicity_triggers`
- [ ] 2.2 Apply design decision 2 to `skills/agent-process/always-on.md` and record its characters before and after with `python -c "import subprocess,sys;print(len(subprocess.run(['git','show',sys.argv[1]],capture_output=True,encoding='utf-8').stdout))" <rev>:skills/agent-process/always-on.md` (`main`, then the staged copy `:skills/agent-process/always-on.md` after `git add`); verify `tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file` and `tests/publisher/test_plugin.py::test_publisher_dogfoods_process`
- [ ] 2.3 Apply design decision 4 to `skills/agent-process/SKILL.md`, the §V external-system row of decision 1 to its `## Proposal` platform-behaviour bullet and decision 5's last row to its `## Delivery` report sentence; verify `test_skill_carries_principles_core_and_harness_tactics`
- [ ] 2.4 Apply design decision 3 to the `Policy source` and `P0`/`P1` bullets of `.agent-process/REVIEW_CONTRACT.md` and to step 2 of `agents/architect-reviewer.md` (spec review-and-merge: The review contract labels each principle); verify `tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle` and `tests/publisher/test_plugin.py`
- [ ] 2.5 Apply decision 1's `openspec/config.yaml` line 20 edit (spec planning: Architect review is the last step of the propose run) (spec implementation: RED first for behavioural changes) and repoint the §IV link of `.agent-process/docs/adr/0011-agentic-process-distribution-mechanism.md` to the `#operative-principles` anchor of `always-on.md`; verify `tests/agent_process/test_doc_links.py` and that `git grep -n "principles.md" -- skills agents .agent-process/REVIEW_CONTRACT.md openspec/config.yaml openspec/specs tests` prints only the `navigation_policy.py` size comment
- [ ] 2.6 Write `.agent-process/docs/adr/0045-each-principle-has-one-home.md`: decisions 1, 2, 4 and 5 with their alternatives, naming the archived `design.md` in plain text, not as a link, for the destination tables instead of copying them; that it supersedes what ADRs 0016, 0043 and 0044 say of `principles.md`; the character counts of 2.2 with the token estimate at 3.7 characters per token; deletion condition: none while `always-on.md` is the canon; verify `tests/agent_process/test_adr_records.py`
- [ ] 2.7 Commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change principles-one-home`, then `gh pr create --title "feat: principles-one-home" --body-file <report>`; the report names tracking issue 443 as a plain reference, carries the scenario-to-test map, links ADR 0045 for the destination tables, gives the `always-on.md` character change, and states the principles it interacts with (§I–VII, goal 2)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| roles / A consumer reads principles and tactics from the skill | `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` |
| review-and-merge / Contract and principles | `tests/publisher/test_reusable_workflows.py::test_review_contract_names_the_narrow_simplicity_triggers` |
| review-and-merge / Each principle has a severity | `tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle` |
| planning / Review finding | n/a: a reviewer's judgement; the delta only repoints the requirement's file reference |
| planning / Review class without evidence | `tests/publisher/test_start_change.py::test_review_not_valid` |
| planning / Over-long rule or bespoke check | `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check` |
| planning / Plan without a prior issue | `tests/publisher/test_start_change.py::test_plan_without_a_prior_issue` |
| planning / Addition without evidence | `tests/publisher/test_start_change.py::test_addition_without_evidence` |
| planning / Rework verdict | `tests/publisher/test_planning_workflow.py::test_rework_verdict` |
| planning / Plan approved | `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue` |
| planning / Existing tracking issue | `tests/publisher/test_start_change.py::test_existing_tracking_issue` |
| planning / Review archives with the change | `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change` |
| planning / Review round | `tests/publisher/test_planning_workflow.py::test_review_round` |
| implementation / Behavioural change | `tests/publisher/test_check_red.py::test_behavioural_change` |
| implementation / Runner given | `tests/publisher/test_check_red.py::test_behavioural_change` |
| implementation / No python on PATH | `tests/publisher/test_check_red.py::test_no_python_on_path` |
| implementation / Configuration that cuts the run | `tests/publisher/test_check_red.py::test_interrupted_run_is_no_verdict` |
| implementation / No quality command declared | `tests/publisher/test_check_red.py::test_refuses_without_quality_declaration` |
| implementation / Run leaves the tree clean | `tests/publisher/test_check_red.py::test_run_leaves_the_tree_clean` |
| maintenance / Narrative issue reference | `tests/agent_process/test_issue_refs.py::test_issue_reference_outside_history` |
| maintenance / History record keeps its references | `tests/agent_process/test_issue_refs.py::test_history_record_keeps_its_references` |
