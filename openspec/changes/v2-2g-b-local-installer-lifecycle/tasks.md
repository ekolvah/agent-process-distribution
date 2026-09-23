## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-2g-b-local-installer-lifecycle --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 155; verify it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 Add the fixture: a local bare repository built in `tmp_path` whose tag `v2.0.0` carries this tree's `skills/agent-process/` and whose tag `v2.1.0` carries a recording stub `init.py` (prints argv, `cwd`, a marker; exits with a chosen code), selected through `AGENT_PROCESS_REPOSITORY` (design D6); verify it builds with `python -m pytest tests/publisher/test_init.py -q -k fixture`
- [x] 1.2 Add to `tests/publisher/test_init.py`: `test_lifecycle` (the {fresh, same-version, upgrade} × {dry-run, confirm, retry} × {win32, linux} table), `test_other_version_dry_run_leaves_no_state`, `test_confirm_selects_release_before_composing`, `test_skill_link_resolves_to_selected_release`, `test_retry_after_each_write` (parametrized over the write labels of an uninterrupted fresh and upgrade run), `test_rerender_replaces_only_owned_content` (design D6), `test_conflict_fails_closed` (one case per row of design D4 and each D3 conflict state), `test_installed_footprint_is_closed` (real pinned OpenSpec), `test_no_remote_write`, `test_literal_commands_are_yaml_safe`, `test_caller_inputs`, `test_empty_test_command_is_refused`, `test_version_matches_plugin`, and `test_capture_contract` (UTF-8, `None` preserved); give `init.py` a signature stub so each fails in its body
- [x] 1.3 In `tests/publisher/test_plugin.py` rename `test_package_has_no_installer_state` to `test_package_contents_are_closed` and make it expect `SKILL.md`, the seven scripts, `scripts/init.py`, and exactly the four templates, still rejecting any hook, ruleset, or protection file; add `init.py` to the script set of `test_shared_skill_owns_the_procedure_and_scripts` and of `tests/publisher/test_delivery_scripts.py`
- [x] 1.4 Run `python skills/agent-process/scripts/check_red.py` with the node ids of 1.2 and `tests/publisher/test_plugin.py::test_package_contents_are_closed`; verify it exits 0 with each RED; commit as `test(distribution): RED for the local installer lifecycle`

## 2. Templates and installer

- [x] 2.1 Add the four templates of design D4 under `skills/agent-process/templates/`; verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_plugin.py -q -k "caller_inputs or yaml_safe or package_contents"` is green
- [x] 2.2 Implement the release ownership of design D1 (temporary-clone dry-run, forwarded output and exit code, confirm hand-off, `--selected-release` guard, visible repository override); verify `python -m pytest tests/publisher/test_init.py -q -k "other_version_dry_run or selects_release or version_matches"` is green
- [x] 2.3 Implement preflight and the fixed write order of design D2 and the checkout/link reconciliation of design D3 (staged clone plus `os.replace`, `shutil.which` for every executable, symlink or junction per platform); verify `python -m pytest tests/publisher/test_init.py -q -k "skill_link or conflict_fails_closed"` is green
- [x] 2.4 Implement consumer ownership, rendering, and atomic writes of design D4 and the `on_write` seam of design D6; verify `python -m pytest tests/publisher/test_init.py -q` is green, including `test_lifecycle`, `test_retry_after_each_write`, `test_installed_footprint_is_closed`, and `test_no_remote_write`; then run `python -m pytest tests/publisher/test_init.py -q` on a Windows host and keep its output for the PR report (design D6); commit Group 2 as `feat(distribution): local installer lifecycle`

## 3. Entry points and docs

- [x] 3.1 Add `commands/init.md` and the `## Install` section of `skills/agent-process/SKILL.md` (design D7), and point the retired note of `.agent-process/docs/architecture/agent-process-installation.md` at that section; verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py tests/agent_process/test_doc_links.py tests/agent_process/test_doc_headers.py -q` is green; commit as `docs(distribution): install entry points`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify every change and spec passes
- [x] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify it passes; confirm `git diff --name-only origin/main` lists only the paths of the proposal's Impact and no workflow, ruleset, or Project file of this repository

## 5. Deliver

- [ ] 5.1 With a clean worktree run `python skills/agent-process/scripts/archive_change.py v2-2g-b-local-installer-lifecycle`; verify it applies the `distribution` delta, commits the archive, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "v2-2g-b-local-installer-lifecycle" --body-file <report>`; the report references issue 155 without `Closes`, carries the scenario → test map, names issues 156, 153, 154, 114 as excluded ownership, and carries the Windows-host run of task 2.4, and records under deferrals that issue 153 must declare exactly the `setup` and `test` inputs the caller template passes (design D5)
- [ ] 5.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`; after each corrective push run both again; resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`, answer P2/P3 without resolving, run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- `distribution / Dry-run of another version` → `tests/publisher/test_init.py::test_other_version_dry_run_leaves_no_state`
- `distribution / Confirmed upgrade` → `tests/publisher/test_init.py::test_confirm_selects_release_before_composing`
- `distribution / Link on Windows and Unix` → `tests/publisher/test_init.py::test_skill_link_resolves_to_selected_release`
- `distribution / Retry after an interrupted write` → `tests/publisher/test_init.py::test_retry_after_each_write`
- `distribution / Target the installer does not own` → `tests/publisher/test_init.py::test_conflict_fails_closed`
- `distribution / Fresh repository` → `tests/publisher/test_init.py::test_installed_footprint_is_closed`
- `distribution / Installation of another release` → `tests/publisher/test_init.py::test_rerender_replaces_only_owned_content`
- `distribution / Confirmed run` → `tests/publisher/test_init.py::test_no_remote_write`
- `distribution / Process change` → `tests/publisher/test_plugin.py::test_package_contents_are_closed` and `tests/publisher/test_plugin.py::test_publisher_dogfoods_process`
