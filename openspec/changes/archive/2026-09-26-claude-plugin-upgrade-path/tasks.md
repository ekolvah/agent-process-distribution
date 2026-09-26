## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py claude-plugin-upgrade-path --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 184. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 `tests/publisher/test_start_change.py`: add `test_skill_behind_names_observed_path`, parametrized over both scripts with a recorded release newer than `VERSION`. It asserts that `main` exits 2 and that stderr names `claude plugin marketplace add "ekolvah/agent-process-distribution#v<recorded>"`, `~/.claude/settings.json`, `claude plugin update agent-process@agent-process-marketplace`, `--scope`, and `--version <recorded>`, and does not name `/plugin marketplace update`. It also asserts that `restart` occurs after the declaration and again after `claude plugin update` (the two restarts of #184 comment 5844817104, steps G and I). Set `_SKILL_FIX` to `claude plugin update` so the `newer` case of `test_release_drift` asserts the new fix
- [x] 1.2 `tests/publisher/test_planning_workflow.py::test_install_names_the_skill_marker`: assert that `## Install` names `claude plugin marketplace add`, `~/.claude/settings.json` and `claude plugin update agent-process@agent-process-marketplace`, and still names `enabling the plugin for the project`. It asserts that `## Install` no longer names `/plugin marketplace update`
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py` with the tests of 1.1–1.2, including `test_release_drift`. Verify that all are RED, then commit as `test(distribution): release drift names the observed Claude upgrade path (RED)`

## 2. Upgrade path

- [x] 2.1 `release_drift` in `skills/agent-process/scripts/init.py`: the skill-behind branch names the Claude path and the Codex `--version <recorded>` (design: The message carries the commands; `add` or an edit of the declaration). Verify that `python -m pytest tests/publisher/test_start_change.py -q` is green
- [x] 2.2 `## Install` of `skills/agent-process/SKILL.md`: replace the sentence on the ignored project `ref` (#184) and the `/plugin marketplace update` remedy with the observed mechanism. The user-scope declaration pins the release for every repository on the machine, and the path to a release is the one of 2.1. That path answers a plugin that is behind or that has no skill. The remedy `enabling the plugin for the project` stays for the reason "not enabled for this project" (design: Install rewrite scope). Verify that `python -m pytest tests/publisher -q` is green, then commit Group 2 as `fix(distribution): name the observed Claude upgrade path`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py claude-plugin-upgrade-path`. Verify that it applies the `distribution` delta, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "claude-plugin-upgrade-path" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`), carries the scenario → test map, and names the deferral: the version-string cache collision gets its own issue (design: Non-Goals)
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution / Release recorded` → `tests/publisher/test_init_config.py::test_config_block_records_release` (unchanged)
- `distribution / Release drift` → `tests/publisher/test_start_change.py::test_release_drift`
- `distribution / Skill behind the project` → `tests/publisher/test_start_change.py::test_skill_behind_names_observed_path`
- `distribution / Publisher checkout` → `tests/publisher/test_start_change.py::test_publisher_checkout_is_exempt` (unchanged)
