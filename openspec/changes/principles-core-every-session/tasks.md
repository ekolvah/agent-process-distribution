## 0. Delivery start

- [ ] 0.1 Confirm `openspec/changes/archive/` on `origin/main` holds `consumer-neutral-principles`, `delegate-exploration-reads` and `review-checks-every-principle`, then diff on `origin/main`: the roles requirement against this change's roles delta, the review-and-merge requirement against this change's review-and-merge delta, §III, §IV and §VI of `principles.md` and the contract's `Policy source` and `P0`/`P1` clauses against the texts design D2 edits. Any difference other than this change's own edits (D2) stops the run: revise the plan with `/opsx:update` and review it again before RED
- [x] 0.2 Run `agent-process start_change principles-core-every-session --planner Claude --implementer Claude` (tracking issue 429), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 Apply design D5 to `tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file`, `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` and `tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle`
- [ ] 1.2 Run `agent-process check_red` with the node ids of 1.1 and commit RED with these ticks

## 2. One wording

- [ ] 2.1 Insert design D1's section between `## Goal function` and `## Claude harness` of `skills/agent-process/always-on.md` and apply design D3 to that file and `CLAUDE.md` (spec distribution: An installed repository's sessions carry the goal function); verify `test_rules_carry_the_always_on_file`, `test_publisher_dogfoods_process` and `tests/publisher/test_init_conflicts.py::test_conflict_fails_closed`
- [ ] 2.2 Apply design D2 to `skills/agent-process/principles.md`, `SKILL.md` and `.agent-process/REVIEW_CONTRACT.md` (spec review-and-merge: The review contract labels each principle) (spec roles: The skill carries the principles core and harness tactics); verify `test_skill_carries_principles_core_and_harness_tactics`, `tests/publisher/test_reusable_workflows.py`, `tests/agent_process/test_doc_links.py` and `tests/agent_process/test_doc_headers.py`
- [ ] 2.3 Write `.agent-process/docs/adr/0044-operative-principles-reach-every-session.md` (design D1 with its alternatives, D2, D4 with `git show main:skills/agent-process/always-on.md | wc -c`, `wc -c skills/agent-process/always-on.md` and their token estimate at 3.7 characters per token; deletion condition: Claude Code loads a plugin's instructions into every session natively); verify `tests/agent_process/test_adr_records.py`
- [ ] 2.4 Commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change principles-core-every-session`, then `gh pr create --title "feat: principles-core-every-session" --body-file <report>`; the report names tracking issue 429 as a plain reference, carries the scenario-to-test map and both `wc -c` figures with their token estimate, and states the MINOR amendment and the principles it interacts with (§I–VII, goal 2)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Rules file written | `tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file` |
| distribution / Unmanaged rules file | `tests/publisher/test_init_conflicts.py::test_conflict_fails_closed` case `rules-unmanaged` |
| roles / A consumer reads principles and tactics from the skill | `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` |
| review-and-merge / Each principle has a severity | `tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle` |
