## 0. Delivery start

- [x] 0.1 Run `agent-process start_change install-reports-post-merge-steps --planner Claude --implementer Claude` (tracking issue 474), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/init_harness.py` give the fake GitHub an `allow_auto_merge = False` attribute returned with `default_branch` in its `repos/<owner>/<name>` read and a `required_checks: list[str] = []` attribute returned as one `required_status_checks` rule by a new `repos/<owner>/<name>/rules/branches/<default>` read, and add a `local_settings(sandbox, token)` helper writing `.claude/settings.local.json`. In `tests/publisher/test_init_remote.py` add, each parametrized `--dry-run` / `--confirm`: `test_protection_inactive_is_manual` (only `agent-process / quality` required) — exit 0 and one `manual protection` row containing `activate_protection --pr`, `--dry-run` and `--confirm`; `test_agent_identity_pending_is_manual` (parametrized also over no settings file and a settings file `{"permissions": {}}`; auto-merge on) — exit 0 and one `manual agent-identity` row without `(cannot read: ` containing `gh auth login -s project,workflow`, `gh auth switch --user` and `manual.IDENTITY_FIX`; `test_auto_merge_disallowed_is_manual` (settings with `env.GH_TOKEN`; auto-merge off) — one `manual auto-merge` row containing `gh repo edit --enable-auto-merge` and no `agent-identity` row. In `test_observed_manual_rows_are_omitted` call `local_settings`, set `allow_auto_merge = True` and require both process checks. In `test_unreadable_manual_state_is_printed` add three cases: `repo-read` — a new fake GitHub fault, documented in its docstring, where the `repos/<owner>/<name>` read prints GitHub's error body (`{"message": "Not Found", "status": "404"}`, so neither `allow_auto_merge` nor `default_branch`) and exits 1, in a non-empty sandbox so `init`'s own empty-repository read is not hit; expect the `protection` and `auto-merge` rows each with `(cannot read: `; `rules-read` — a new fault where the `rules/branches` read prints the same error body and exits 1; expect the `protection` row with `(cannot read: `; `settings-malformed` — a settings file that is not JSON, and `settings-shape` — a settings file whose `env` is a list; expect the `agent-identity` row with `(cannot read: `
- [x] 1.2 In `tests/publisher/test_skill_check.py::test_identity_missing` assert each text also contains `--confirm`, `gh repo edit --enable-auto-merge` and `restart Claude Code`; add `test_identity_fix_is_one_text` asserting `_check().IDENTITY_FIX == manual.IDENTITY_FIX`, beside the `PRE_COMMIT_ID` test
- [x] 1.3 Run `agent-process check_red tests/publisher/test_init_remote.py::test_protection_inactive_is_manual tests/publisher/test_init_remote.py::test_agent_identity_pending_is_manual tests/publisher/test_init_remote.py::test_auto_merge_disallowed_is_manual "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[repo-read]" "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[rules-read]" "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[settings-malformed]" "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[settings-shape]" tests/publisher/test_skill_check.py::test_identity_missing tests/publisher/test_skill_check.py::test_identity_fix_is_one_text` and commit RED with these ticks

## 2. Identity is reported

- [x] 2.1 `skills/agent-process/scripts/manual.py` (design D1, D2): add `IDENTITY_FIX` and the `protection`, `agent-identity` and `auto-merge` rows via `_outstanding`, reading the settings with `_plugin_file`, and the repository and its default branch's rules with `_gh_read`; the contexts come from `activate_protection`; a rules or repository read that is not the expected shape (an error object instead of a rule list, an absent `allow_auto_merge` or `default_branch`) and settings that are not an object, or whose `env` is present and not an object, raise `Unreadable`; a missing `env` is `{}`, as in `agent_identity._settings`. Verify `python -m pytest tests/publisher/test_init_remote.py -q` is green
- [x] 2.2 `skills/agent-process/templates/skill_check.py` (design D2): `IDENTITY_FIX` names the dry-run, `--confirm`, `gh repo edit --enable-auto-merge` and the restart; the advice sentence no longer repeats them; update the module docstring. Verify `python -m pytest tests/publisher/test_skill_check.py tests/publisher/test_plugin.py -q` is green
- [x] 2.3 `skills/agent-process/SKILL.md` Install step 4: name the `protection` row, done in step 5, the `agent-identity` row, done in step 6, and the `auto-merge` row among the rows to tell the person. Verify `python -m pytest tests/publisher -q -k "skill or planning"` is green, then commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change install-reports-post-merge-steps`, then `gh pr create --title "fix: install-reports-post-merge-steps" --body-file <report>`. The report names tracking issue 474 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §I, §III, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Protection inactive | `tests/publisher/test_init_remote.py::test_protection_inactive_is_manual` |
| distribution / Identity pending | `tests/publisher/test_init_remote.py::test_agent_identity_pending_is_manual`, `tests/publisher/test_skill_check.py::test_identity_fix_is_one_text` |
| distribution / Auto-merge disallowed | `tests/publisher/test_init_remote.py::test_auto_merge_disallowed_is_manual` |
| distribution / Observed done | `tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted` (gains the three states) |
| distribution / Unreadable state | `tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed` (gains `repo-read`, `rules-read`, `settings-malformed`, `settings-shape`) |
| distribution / Identity missing | `tests/publisher/test_skill_check.py::test_identity_missing` (gains the full fix) |
| distribution / Identity set | `tests/publisher/test_skill_check.py::test_identity_set` (unchanged) |
