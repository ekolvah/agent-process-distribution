## 0. Delivery start

- [x] 0.1 Run `agent-process start_change planning-standard-first --planner Claude --implementer Claude` (tracking issue 451), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_planning_workflow.py` add `test_design_on_an_external_tool`. It asserts these phrases in `_section("Proposal")`: `usage guidance`, `external tool, model or API`, `built around`, `new to the repository`, `standard approach to the problem`, `## Standard approach`, `URL`, `none found:`, `what was searched`, and in `_section("Architect review")` `## Standard approach` and `goes back to the planner`. Extend the `bespoke` phrase tuple of `test_over_long_rule_or_bespoke_check` with `## Standard approach`, `standard approach to the problem`, `none found`, `convincing` and `follows or departs`
- [x] 1.2 In `tests/publisher/test_start_change.py` add `test_plan_without_a_standard_approach`: rejected — an `approve` change with no `## Standard approach` in `proposal.md` or `design.md`; a section with neither a URL nor `none found:` with text; `none found:` with nothing after it; a URL only under the next `##` section — each on the placeholder (with `--area`) and on an existing number; `create_tracking_issue` exits 2, stderr names `## Standard approach`, `creates(gh) == []` and `gh.edits() == []`; accepted — the section in `design.md` alone, with a `###` subheading before its URL, reaches `set_status`. In `tests/publisher/delivery_fakes.py` give `make_change`'s `proposal.md` a `## Standard approach` section with `none found: fixture` so the other tail tests keep passing
- [x] 1.3 Run `agent-process check_red` with the node ids of 1.1 and 1.2 and commit RED with these ticks

## 2. Standard approach first

- [ ] 2.1 Apply design decision 1 to the first bullet of `## Proposal` in `skills/agent-process/SKILL.md` (spec planning: Design on an external tool)
- [ ] 2.2 Apply design decision 2 to the `bespoke` description in `skills/agent-process/architect-review.schema.json` (spec planning: Over-long rule or bespoke check)
- [ ] 2.3 Apply design decision 3 in `skills/agent-process/scripts/create_tracking_issue.py`: the section check after the verdict, before either branch, and one docstring sentence; in `SKILL.md` `## Architect review`, after "send its errors back to the reviewer", say that a missing section goes back to the planner, who adds it and reviews again (spec planning: Plan without a standard approach)
- [ ] 2.4 Apply design decision 4: add the bullet to `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md` after the `additions` removal entry
- [ ] 2.5 Verify `python -m pytest tests/publisher/test_planning_workflow.py tests/publisher/test_start_change.py tests/agent_process/test_issue_refs.py tests/agent_process/test_adr_records.py -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change planning-standard-first`, then `gh pr create --title "feat: planning-standard-first" --body-file <report>`; the report names tracking issue 451 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §IV, §VII, Scripts over instructions)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| planning / Ambiguous scope | n/a: person and planner behaviour; the delta leaves it unchanged |
| planning / Design on an external tool | `tests/publisher/test_planning_workflow.py::test_design_on_an_external_tool` |
| planning / Review finding | `tests/publisher/test_planning_workflow.py::test_review_finding` |
| planning / Review class without evidence | `tests/publisher/test_start_change.py::test_review_not_valid` |
| planning / Over-long rule or bespoke check | `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check` |
| planning / Validator scope | n/a: the person's judgement of content; the form check is `test_plan_without_a_standard_approach` |
| planning / Plan without a standard approach | `tests/publisher/test_start_change.py::test_plan_without_a_standard_approach` |
| planning / Plan without a prior issue | `tests/publisher/test_start_change.py::test_plan_without_a_prior_issue` |
| planning / Addition without evidence | `tests/publisher/test_start_change.py::test_addition_without_evidence` |
| planning / Rework verdict | `tests/publisher/test_planning_workflow.py::test_rework_verdict` |
| planning / Plan approved | `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue` |
| planning / Existing tracking issue | `tests/publisher/test_start_change.py::test_existing_tracking_issue` |
| planning / Review archives with the change | `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change` |
| planning / Review round | `tests/publisher/test_planning_workflow.py::test_review_round` |
