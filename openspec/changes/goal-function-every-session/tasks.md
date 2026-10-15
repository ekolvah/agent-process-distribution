## 0. Delivery start

- [x] 0.1 Run `agent-process start_change goal-function-every-session --planner Claude --implementer Claude` (tracking issue 414), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 Apply the test edits of design D5 to `tests/publisher/init_harness.py`, `test_init_config.py`, `test_init_conflicts.py` and `test_plugin.py`
- [x] 1.2 Run `agent-process check_red` with the node ids of 1.1 and commit RED with these ticks

## 2. Canonical file

- [x] 2.1 Create `skills/agent-process/always-on.md` from the `## Goal function` section of `principles.md` and the `## Claude harness` section of `SKILL.md`, with no relative link (design D1), and apply design D3 to it (spec roles: The skill carries the principles core and harness tactics); verify `test_skill_carries_principles_core_and_harness_tactics` and `test_package_contents_are_closed`
- [x] 2.2 Replace those two sections in `principles.md` and `SKILL.md` with their link lines, point `SKILL.md` line 17 at the `#goal-function` anchor of `always-on.md`, name `always-on.md` in the Governance delegation paragraph, repoint the §VII goal-function link and ADR 0021's `#scripts-over-instructions` link, and rewrite step 2 of `agents/architect-reviewer.md`, as design D1 says; verify `tests/agent_process/test_doc_links.py` and `tests/agent_process/test_doc_headers.py`
- [x] 2.3 Commit the group with its ticks

## 3. Installer

- [ ] 3.1 Add the `rules` step of design D2 to `init.py`, with its docstring entry and the renumbered steps (spec distribution: An installed repository's sessions carry the goal function; The installed footprint is closed); verify `tests/publisher/test_init_config.py`, `test_init_conflicts.py` and `test_init_remote.py`
- [ ] 3.2 In the `#install` section of `SKILL.md`, after the session-start environment sentence, say that Install's `.claude/rules/agent-process.md` puts the goal function and the Claude harness into every session of the repository, compaction included; verify `tests/agent_process/test_doc_links.py`
- [ ] 3.3 Commit the group with its ticks

## 4. Dogfood and record

- [ ] 4.1 In `CLAUDE.md`, replace the Claude harness link with the line `@skills/agent-process/always-on.md` (spec distribution: This repository dogfoods its own process); verify `test_publisher_dogfoods_process`
- [ ] 4.2 Write `.agent-process/docs/adr/0043-the-goal-function-reaches-every-session.md` (design D1, D2 with its alternatives, D3; deletion condition: Claude Code loads a plugin's instructions into every session natively); verify `tests/agent_process/test_adr_records.py`
- [ ] 4.3 Commit the group with its ticks

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits
- [ ] 5.2 Run `openspec validate --strict --all`
- [ ] 5.3 Run the `test` that `.github/agent-process-quality.json` declares

## 6. Deliver

- [ ] 6.1 Comment on issue 414 with the scope-1 observation (proposal.md, Why) and the outcome of each rule with its reason (design D3)
- [ ] 6.2 Run `agent-process archive_change goal-function-every-session`, then `gh pr create --title "feat: goal-function-every-session" --body-file <report>`; the report names tracking issue 414 as a plain reference, carries the scenario-to-test map, and states the MINOR amendment of the goal function and the principles it interacts with (goal 2, §VII)
- [ ] 6.3 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Rules file written | `tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file` |
| distribution / Unmanaged rules file | `tests/publisher/test_init_conflicts.py` case `rules-unmanaged` |
| distribution / Repository instructions | `tests/publisher/test_plugin.py::test_publisher_dogfoods_process` |
| distribution / Fresh repository | `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed` (`CONSUMER_FILES`) |
| distribution / Installation of another release | `tests/publisher/test_init_config.py::test_rerender_replaces_only_owned_content` (`CONSUMER_FILES`) |
| distribution / Repository settings | `tests/publisher/test_plugin.py::test_publisher_dogfoods_process` |
| distribution / Process change | n/a: the scenario's text is unchanged by this change |
| roles / A consumer reads principles and tactics from the skill | `tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` |
