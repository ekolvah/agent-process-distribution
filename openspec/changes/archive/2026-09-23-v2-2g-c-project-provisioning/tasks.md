## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py v2-2g-c-project-provisioning --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 156; verify it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work

## 1. RED first

- [x] 1.1 In `tests/publisher/test_init.py` add `FakeGitHub` behind `Runner` (design D6: the two reads in the observed shapes, `copy` and `link` applied to its Projects, per-command `fail-before`/`fail-after`, template Project 4 owned by `ekolvah` and linked to the publisher); include its state in `_final` and key `gh-copy`/`gh-link` in `state_changing`; verify the fixture builds with `python -m pytest tests/publisher/test_init.py -q -k fixture`
- [x] 1.2 Add `test_project_states` (every row of design D2 plus the truncated list; rows, exit code, and an unchanged snapshot of `root`, `home`, and the fake on each conflict; no read 2 on the linked rows), `test_project_command_faults` ({copy, link} × {fail-before, fail-after}; copy and link counts across run and retry), and `test_manual_actions_are_printed`; rename `test_no_remote_write` to `test_only_project_writes_remote` (exactly one copy and one link, no other GitHub write) and add `test_dry_run_writes_nothing_remote` (both reads issued, no write) (design D5–D6); verify each fails in its body
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py` with the node ids of 1.2; verify it exits 0 with each RED (`test_retry_after_each_write` is not listed: it derives its labels from its own reference run and turns green with the implementation in 2.2); commit as `test(distribution): RED for recoverable Project provisioning`

## 2. Project phase

- [x] 2.1 Implement the two reads and the classification of design D1–D2 as steps 9–10 in the preflight (the truncated list is an `InstallError`); verify `python -m pytest tests/publisher/test_init.py -q -k "project_states or dry_run_writes_nothing"` is green
- [x] 2.2 Implement copy and link with the re-read of design D3; verify `python -m pytest tests/publisher/test_init.py -q -k "project_command_faults or retry_after_each_write or only_project_writes_remote"` is green
- [x] 2.3 Implement the `manual` rows of design D4 and update the module docstring's step list and remote-write sentence; verify `python -m pytest tests/publisher/test_init.py -q` is green; commit Group 2 as `feat(distribution): recoverable Project provisioning`

## 3. Entry points and live read

- [x] 3.1 In `skills/agent-process/SKILL.md` `## Install`, replace "never … writes GitHub settings" with the Project copy and link as the only GitHub writes, and state that `gh` must be authenticated with the `project` scope; verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_planning_workflow.py tests/agent_process/test_doc_links.py -q` is green
- [x] 3.2 From this repository's root run `python skills/agent-process/scripts/init.py --test "python .agent-process/scripts/ci_check.py" --dry-run` (reads only; design D6); verify it prints `unchanged project-copy` and `unchanged project-link` for Project 4 and the two `manual` rows whatever its exit code, and keep the output for the PR report; commit Group 3 as `docs(distribution): Project write in the install procedure`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify every change and spec passes
- [x] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify it passes; confirm `git diff --name-only origin/main` lists only the paths of the proposal's Impact and the change directory

## 5. Deliver

- [x] 5.1 With a clean worktree run `python skills/agent-process/scripts/archive_change.py v2-2g-c-project-provisioning`; verify it applies the `distribution` delta, including the rename, commits the archive, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "v2-2g-c-project-provisioning" --body-file <report>`; the report references issue 156 without `Closes`, carries the scenario → test map and the output of task 3.2, and names issues 153, 154, and 114 as excluded ownership
- [ ] 5.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`; after each corrective push run both again; resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`, answer P2/P3 without resolving, run `python .agent-process/scripts/review_gate.py <PR>` on the settled head, and stop at `ready-for-human` or the three-round escalation

## Scenario → test map

- `distribution / No Project yet` → `tests/publisher/test_init.py::test_project_states`
- `distribution / Unlinked copy exists` → `tests/publisher/test_init.py::test_project_states`
- `distribution / Ambiguous Projects` → `tests/publisher/test_init.py::test_project_states`
- `distribution / Link failed after the copy` → `tests/publisher/test_init.py::test_project_command_faults`
- `distribution / Link output lost` → `tests/publisher/test_init.py::test_project_command_faults`
- `distribution / Manual actions` → `tests/publisher/test_init.py::test_manual_actions_are_printed`
- `distribution / Confirmed run` → `tests/publisher/test_init.py::test_only_project_writes_remote`
- `distribution / Dry-run` → `tests/publisher/test_init.py::test_dry_run_writes_nothing_remote`
