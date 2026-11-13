## 0. Delivery start

- [x] 0.1 Run `agent-process start_change manual-shared-read-helpers --planner Claude --implementer Claude` (tracking issue 491), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: pure refactor (`skip_specs: true`); no scenario changes, §I exempts it
- [x] 1.2 Per design D2, add the `rules-shape` fault to `tests/publisher/init_harness.py` (`_repo_read` returns `[{"parameters": {}}]`) and the `rules-shape` case (`--dry-run`, `["protection"]`) to `UNREADABLE` in `tests/publisher/test_init_remote.py`; verify `python -m pytest tests/publisher/test_init_remote.py -q -k rules-shape` is green on the unchanged scripts, then commit it with the group 1 ticks

## 2. Shared helpers

- [ ] 2.1 Per design D2, add `activate_protection.required_contexts(rules)` and make `wait_for_pr._required` and `manual._protected` call it; verify `grep -n "required_status_checks" skills/agent-process/scripts/wait_for_pr.py skills/agent-process/scripts/manual.py` hits no parsing loop
- [ ] 2.2 Per design D1, replace `_names_or_unreadable`/`_has` and `_field` with `_kept`/`_ok` and make `_repository` raise its shape `Unreadable`; verify `grep -n "_names_or_unreadable\|def _has\|def _field" skills/agent-process/scripts/manual.py` is empty
- [ ] 2.3 Per design D4, rename `_plugin_file` to `_json_file`; verify `grep -rn "_plugin_file" skills/` is empty and `python -m pytest tests/publisher -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change manual-shared-read-helpers`, then `gh pr create --title "refactor: manual-shared-read-helpers" --body-file <report>`. The report names tracking issue 491 as a plain reference, carries the scenario-to-test map, states that item 3 is declined (design D3) and that `wait_for_pr` still exits 1 with a traceback on a malformed `rules/branches` response (design Risks), and names the principles it interacts with (goal 1, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| none | n/a: pure refactor, `skip_specs: true`; the existing suite (3.3) stays green, `test_unreadable_manual_state_is_printed` included, with its new `rules-shape` case (1.2) |
