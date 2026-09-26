## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py skill-presence-check --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 187. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 `tests/publisher/test_skill_check.py`: run `templates/skill_check.py <url>` as a subprocess with a fake `claude` first on PATH that prints a given listing or exits non-zero. `test_loaded_is_silent`: one enabled applicable install with `skills/agent-process/SKILL.md` → exit 0, empty stdout. `test_not_loaded_is_marked`, parametrized: no entry, `enabled: false`, other project only, two installPaths, no `SKILL.md` → exit 0, stdout JSON whose `systemMessage` and `additionalContext` both contain `agent-process skill not loaded` and `SKILL.md#install`. `test_undecidable_is_marked`, parametrized: no `claude` on PATH, exit 1, non-JSON, JSON object instead of list, no URL argument → the same marker with `cannot check`. `test_case_differing_project_paths_are_one_project`: two entries whose `projectPath` differs only in case, same `installPath` → silent
- [x] 1.2 `tests/publisher/test_init.py`: `CONSUMER_FILES` gains `.claude/agent-process-check.py`, the step list gains `check` after `settings`, and `test_installed_footprint_is_closed` expects the `hooks.SessionStart` entry. `test_rerender_replaces_only_owned_content` seeds a consumer `SessionStart` group and a `PreToolUse` hook and asserts both survive while the owned group is replaced. Add `test_installed_consumer_gains_the_hook`: settings with both owned keys equal and no hook → `--confirm` adds the owned group and exits 0; the same in 4-space form → conflict naming the hook group. Add conflict cases `settings-hooks-not-object`, `settings-session-start-not-list` and `check-unmanaged`
- [x] 1.3 `tests/publisher/test_plugin.py`: `TEMPLATES` gains `skill_check.py`; `test_publisher_dogfoods_process` asserts the repository's `SessionStart` group runs `skills/agent-process/templates/skill_check.py`. `tests/publisher/test_planning_workflow.py` `test_install_names_the_skill_marker`: `_section("Install")` contains `agent-process skill not loaded` and `/plugin marketplace update`, and not `pinned per repository`
- [x] 1.4 Run `python skills/agent-process/scripts/check_red.py` with every test of 1.1–1.3 (a `templates/skill_check.py` stub that prints `stub` and exits 1, so every test fails in its body), verify all RED, commit as `test(distribution): a Claude session start reports a missing skill (RED)`

## 2. Check

- [ ] 2.1 `templates/skill_check.py` (design: Check file and hook entry). Verify `python -m pytest tests/publisher/test_skill_check.py -q` is green
- [ ] 2.2 `init.py`: `CHECK = ".claude/agent-process-check.py"`, a `check` file step, the owned `SessionStart` group in `_settings_text`, the footprint comment. `templates/settings.json` gains the hook; this repository's `.claude/settings.json` gains its own group (design: The publisher checks itself). Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_plugin.py -q` is green
- [ ] 2.3 `SKILL.md` `## Install` (design: Install text). Verify `python -m pytest tests/publisher -q` is green, commit Group 2 as `feat(distribution): a Claude session start reports a missing skill`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py skill-presence-check`. Verify that it applies the `distribution` delta, commits the archive, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "skill-presence-check" --body-file <report>`. The report references the tracking issue of task 0.1 with `Closes #187`, carries the scenario → test map, and names the accepted gaps (Codex, #190)
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution / Fresh repository` → `tests/publisher/test_init.py::test_installed_footprint_is_closed`
- `distribution / Installation of another release` → `tests/publisher/test_init.py::test_rerender_replaces_only_owned_content`, `::test_installed_consumer_gains_the_hook`
- `distribution / Skill loaded` → `tests/publisher/test_skill_check.py::test_loaded_is_silent`, `::test_case_differing_project_paths_are_one_project`
- `distribution / Skill not loaded` → `tests/publisher/test_skill_check.py::test_not_loaded_is_marked`
- `distribution / Check cannot decide` → `tests/publisher/test_skill_check.py::test_undecidable_is_marked`
