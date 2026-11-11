## 0. Delivery start

- [x] 0.1 Run `agent-process start_change plugin-channel-settings-auto-update --planner Claude --implementer Claude` (tracking issue 487), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`, replace the `"Enable auto-update"` assertion on the `plugin-channel` row with: `'"autoUpdate": true'` and `~/.claude/settings.json` are in the row, `/plugin` is not, and the indices of `marketplace add` < `plugin install` < `"autoUpdate": true`
- [x] 1.2 Add `test_plugin_channel_reads_user_settings`, parametrized over `(settings, known, row)`: `(True, None, False)`, `(False, True, True)` and `(None, True, False)`. It writes `_plugin_files`, sets the known entry's `autoUpdate` to `known`, and writes `~/.claude/settings.json` of the sandbox home with the `agent-process-marketplace` entry's `autoUpdate` set to `settings`. `None` means the key is dropped, so the entry has no `autoUpdate`, which is the state `marketplace add` leaves. A `--dry-run` then carries a `manual plugin-channel` row exactly when `row` is true
- [x] 1.3 Add a `user-settings-malformed` case to `UNREADABLE`: `--dry-run`, `_plugin_files` written and `~/.claude/settings.json` of the sandbox home written as `not json`, the row `plugin-channel`
- [x] 1.4 Run `agent-process check_red` with the node ids of 1.1–1.3, leaving out the `(None, True, False)` case of 1.2 because it already passes; 2.1 verifies it. Commit RED with the group's ticks

## 2. Implementation

- [x] 2.1 Design decision 3: in `_plugin_channel` (`skills/agent-process/scripts/manual.py`), once the source, `stable` ref and user-scope install hold, read `t.home / ".claude" / "settings.json"` through `_plugin_file`. Take auto-update from its `extraKnownMarketplaces[t.marketplace]["autoUpdate"]` when that key is present, else from the known entry, and let a shape error raise `Unreadable`. Update the docstring. Verify: `python -m pytest tests/publisher/test_init_remote.py -k "plugin_channel or plugin-malformed or user-settings-malformed or observed"`
- [x] 2.2 Design decision 2: in the `plugin-channel` row of `manual.py`, use `claude plugin marketplace add "<source>#stable"`, then `claude plugin install <plugin>`, then `set "autoUpdate": true on its <marketplace> entry in ~/.claude/settings.json`. Verify: `python -m pytest tests/publisher/test_init_remote.py -k manual_actions`
- [x] 2.3 Design decision 2: in `README.md`'s install block, replace the `/plugin` comment line with a comment after `claude plugin install` that names the same settings write. In `skills/agent-process/SKILL.md`'s migration sentence, replace "turn on Enable auto-update for it under `/plugin` → Marketplaces" with "run `claude plugin install agent-process@agent-process-marketplace`, then set `"autoUpdate": true` on its entry in `~/.claude/settings.json`". Verify: `git grep -n "Enable auto-update" -- README.md skills/` prints nothing. Commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change plugin-channel-settings-auto-update`, then `gh pr create --title "feat: plugin-channel-settings-auto-update" --body-file <report>`, then `gh pr merge <PR> --auto --squash`. The report names tracking issue 487 as a plain reference, carries the scenario-to-test map, and states the principles involved (goal 1, goal 3, §I, §IV, §V, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- Channel render: `tests/publisher/test_plugin.py::test_marketplace_follows_stable` (unchanged)
- Machine channel step: `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`
- Auto-update read from user settings: `tests/publisher/test_init_remote.py::test_plugin_channel_reads_user_settings`
