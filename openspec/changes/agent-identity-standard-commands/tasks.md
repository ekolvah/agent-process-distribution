## 0. Delivery start

- [x] 0.1 Run `agent-process start_change agent-identity-standard-commands --planner Claude --implementer Claude` (tracking issue 412), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_init_remote.py` extend `test_agent_identity_pending_is_manual` with tokens reading `ADMIN` and `READ` (row names the permission and `IDENTITY_FIX`), and add `test_agent_identity_holds`, run with another `GH_TOKEN` in the environment (no row; the fake `gh` saw exactly one call carrying the settings token as `GH_TOKEN`, the GraphQL read); extend the fake `gh` of `tests/publisher/init_harness.py` as these need
- [x] 1.2 In `tests/publisher/test_skill_check.py` set `IDENTITY_FIX` to name `Install step 6` and assert `agent_identity` is absent from the marker in `test_identity_missing`
- [x] 1.3 Run `agent-process check_red tests/publisher/test_init_remote.py::test_agent_identity_pending_is_manual tests/publisher/test_init_remote.py::test_agent_identity_holds tests/publisher/test_skill_check.py::test_identity_missing` and commit RED with these ticks

## 2. The row

- [x] 2.1 Extend `manual._identity_set` per design D1, make the row name the failed condition and Install step 6 instead of inline commands, and set `IDENTITY_FIX` in `manual.py` and `templates/skill_check.py` (and its docstring) to "Install step 6 of the agent-process skill, then restart Claude Code"; verify `python -m pytest tests/publisher/test_init_remote.py tests/publisher/test_skill_check.py -q` is green
- [x] 2.2 Delete `skills/agent-process/scripts/agent_identity.py` and `tests/publisher/test_agent_identity.py`, moving `test_approval_ruleset_body` and the `activate_protection` half of `test_a_clone_with_the_agent_identity` into `tests/publisher/test_activate_protection.py`; drop `agent_identity.py` from the script lists of `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`; verify `python -m pytest tests/publisher -q` is green, then commit the group with its ticks

## 3. Runbook and records

- [x] 3.1 Rewrite Install step 6 of `skills/agent-process/SKILL.md` as the runbook of the proposal's **What Changes**, and remove the `Bash(*agent_identity* --confirm*)` ask rule from `.claude/settings.json`; verify `grep -rn "agent_identity" skills .claude/settings.json` prints nothing
- [x] 3.2 Amend ADR 0040 D1, D3, D6 and its Confirmation per design D1–D4 and its deletion condition (no script to remove); verify `grep -n "agent_identity" .agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` prints nothing, then commit the group with its ticks

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument and commit its edits
- [ ] 4.2 Run `openspec validate --strict --all` and the `test` that `.github/agent-process-quality.json` declares

## 5. Deliver

- [ ] 5.1 Run `agent-process archive_change agent-identity-standard-commands`, then `gh pr create --title "feat: agent-identity-standard-commands" --body-file <report>`. The report names tracking issue 412 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, goal 2, §IV for the dropped re-plan, §VII)
- [ ] 5.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Identity pending | `tests/publisher/test_init_remote.py::test_agent_identity_pending_is_manual` |
| distribution / Identity holds | `tests/publisher/test_init_remote.py::test_agent_identity_holds` |
| distribution / Identity missing | `tests/publisher/test_skill_check.py::test_identity_missing` |
| distribution / Identity set | `tests/publisher/test_skill_check.py::test_identity_set` (unchanged) |
| distribution / A clone with the agent's identity | `tests/publisher/test_activate_protection.py::test_a_clone_with_the_agent_identity` (moved) |
| distribution / Installation PR merged | `tests/publisher/test_planning_workflow.py::test_install_continues_past_the_installation_pr` (unchanged) |
| distribution / Unasked upgrade PR merged | `tests/publisher/test_planning_workflow.py::test_upgrade_approval_is_its_consent` (unchanged) |
| review-and-merge / Merge from Claude Code | `tests/publisher/test_activate_protection.py::test_approval_ruleset_body` (moved); live: ADR 0040 Confirmation |
