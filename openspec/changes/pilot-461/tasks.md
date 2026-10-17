## 0. Delivery start

- [x] 0.1 Run `agent-process start_change pilot-461 --planner Claude --implementer Claude` (tracking issue 461), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 Add `## Standard approach` with a URL to the `proposal.md` that `tests/publisher/delivery_fakes.py::make_change` writes, so existing tests keep passing the gate
- [ ] 1.2 Add `tests/publisher/test_start_change.py::test_standard_approach_missing`: no section, a section of plain text, and `none found:` with nothing after it each exit 2 naming `## Standard approach` and "review again" on the placeholder branch, and one of them on the existing-number branch; no create and no edit
- [ ] 1.3 Add `tests/publisher/test_start_change.py::test_standard_approach_recorded`: the section only in `design.md` with `none found: <what was searched>` creates the issue; the fixture's URL in `proposal.md` moves an existing one to `Planned`
- [ ] 1.4 Add `tests/publisher/test_planning_workflow.py::test_departure_from_the_standard`: the `bespoke` description names "every plan", `## Standard approach`, "the standard approach" and "follows or departs from it"; § Proposal names "usage guidance", "industry-standard approach", "## Standard approach" and "none found:"
- [ ] 1.5 Run `agent-process check_red tests/publisher/test_start_change.py::test_standard_approach_missing tests/publisher/test_planning_workflow.py::test_departure_from_the_standard` (`test_standard_approach_recorded` passes before the gate exists) and commit RED with these ticks

## 2. Standard approach gate

- [ ] 2.1 In `create_tracking_issue.py`, after the verdict check, refuse with exit 2 per design.md "Form" (spec planning: Architect review is the last step of the propose run); extend the module docstring; verify both scenario tests
- [ ] 2.2 Extend the `bespoke` description in `architect-review.schema.json` with the content judgement (design.md "Content is the `bespoke` class"); verify `test_departure_from_the_standard` and `test_over_long_rule_or_bespoke_check`
- [ ] 2.3 Open § Proposal of `skills/agent-process/SKILL.md` with the standard-approach step; verify `test_departure_from_the_standard`
- [ ] 2.4 Add the bullet to ADR 0027 after the `additions` removal (design.md "Unlike the removed `additions` regex"); verify `tests/agent_process/test_adr_records.py`
- [ ] 2.5 Commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change pilot-461`, then `gh pr create --title "feat: pilot-461" --body-file <report>`; the report names the tracking issue as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (§VI, §VII, goal 1)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| planning / Standard approach missing | `tests/publisher/test_start_change.py::test_standard_approach_missing` |
| planning / Standard approach recorded | `tests/publisher/test_start_change.py::test_standard_approach_recorded` |
| planning / Departure from the standard | `tests/publisher/test_planning_workflow.py::test_departure_from_the_standard` |
| planning / Review finding | `tests/publisher/test_planning_workflow.py::test_review_finding` |
| planning / Review class without evidence | `tests/publisher/test_start_change.py::test_review_not_valid` |
| planning / Over-long rule or bespoke check | `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check` |
| planning / Plan without a prior issue | `tests/publisher/test_start_change.py::test_plan_without_a_prior_issue` |
| planning / Addition without evidence | `tests/publisher/test_start_change.py::test_addition_without_evidence` |
| planning / Rework verdict | `tests/publisher/test_planning_workflow.py::test_rework_verdict` |
| planning / Plan approved | `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue` |
| planning / Existing tracking issue | `tests/publisher/test_start_change.py::test_existing_tracking_issue` |
| planning / Review archives with the change | `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change` |
| planning / Review round | `tests/publisher/test_planning_workflow.py::test_review_round` |
| planning / Validator scope | n/a: the person judges content; no script can prove the absence of a judgement |
