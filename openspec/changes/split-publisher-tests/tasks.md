## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py split-publisher-tests --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 193. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 no RED: move of tests, no behaviour change (`skip_specs`); the safety net is the moved tests themselves. Record the baseline instead: `python -m pytest tests/publisher --collect-only -q` reports `384 tests collected`, and its node ids with the module path stripped (`sed 's/^.*:://' | sort`) are saved in the scratchpad for 3.2 (design D6)

## 2. Move

- [x] 2.1 Split `test_delivery_scripts.py` and `test_release_drift.py` into `test_check_red.py`, `test_set_status.py`, `test_start_change.py`, `test_pr_delivery.py` (design D1, D4) and delete both sources. Verify `python -m pytest tests/publisher/test_check_red.py tests/publisher/test_set_status.py tests/publisher/test_start_change.py tests/publisher/test_pr_delivery.py -q` is green
- [x] 2.2 Move the shared `test_init.py` names to `init_harness.py` and the three sections to `test_init_config.py`, `test_init_conflicts.py`, `test_init_remote.py` (design D2, D4). Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_config.py tests/publisher/test_init_conflicts.py tests/publisher/test_init_remote.py -q` is green
- [x] 2.3 Move `OPENSPEC` and `_openspec` to `tests/publisher/openspec_cli.py` and import them from `test_openspec_valid.py` and `test_planning_workflow.py` (design D3). Verify both modules pass under `python -m pytest`; commit Group 2 as `test(publisher): split test modules under the module size limit`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `python -m pytest tests/publisher --collect-only -q` reports `384 tests collected` and its stripped node ids equal the 1.1 baseline, that no `tests/publisher/*.py` exceeds 700 lines, that a search for `from tests\.\w+\.test_|import tests\.\w+\.test_` under `tests/` finds nothing, and that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py split-publisher-tests`. Verify that it commits the archive (no spec delta: `skip_specs`) and pushes the branch
- [ ] 4.2 Run `gh pr create --title "split-publisher-tests" --body-file <report>`. The report names the tracking issue of task 0.1 as a plain reference (never `Closes`), carries the scenario → test map, and names the deviations from the issue (fixtures stay in `test_start_change.py`; `test_init.py` split by its sections; the `openspec_cli.py` move; no permanent import guard, design D5 and #194)
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- n/a: `skip_specs` — the change has no delta scenario; behaviour is held by the moved tests, whose collected ids are unchanged (task 3.2).
