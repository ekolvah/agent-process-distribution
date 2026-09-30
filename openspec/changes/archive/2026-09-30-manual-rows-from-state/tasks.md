## 0. Delivery start

- [x] 0.1 Run `agent-process start_change manual-rows-from-state --planner Claude --implementer Claude` for tracking issue 269. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/manual-rows-from-state`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Harness (design D5), `tests/publisher/init_harness.py`: `Project` gains `public` (default false), `workflows` (name → enabled) and `areas` (option names); the template Project 4 is public with the eight observed workflows and the five observed `Area` options; `project copy` appends a private copy with those options and every workflow but `Auto-add to project`. `FakeGitHub` gains `secrets: set[str]` and answers `secret list --repo <consumer> --json name` (fault `secret-list` → exit 1 with the observed 403 stderr), gains the fault `project-read` (the GraphQL `projectV2(number:` read exits 1 with a stderr line), and answers a GraphQL query that reads `projectV2(number:` by its `login`/number variables from `Project` fields, in the observed shape. `test_init_remote.py` `_gh_kind` classifies `secret list` as `read`. Verify `python -m pytest tests/publisher -q` stays green before any new assertion
- [x] 1.2 Tests in `tests/publisher/test_init_remote.py`: `test_manual_actions_are_printed` (both modes) — `--confirm` prints the three `project-*` rows with the workflows row naming `Auto-add to project` and none of `Item added`, `Item reopened`, `Item closed`, `Pull request merged`; `--dry-run` prints the three with `(cannot read: ` (no linked Project yet); the plugin-channel and pre-push assertions stay; in both modes the `manual` rows are the output's last lines (no non-`manual` line follows the first `manual` line). New `test_observed_manual_rows_are_omitted` (both modes): secret set, a linked public Project with all workflows enabled and `Area` options `["Alpha"]`, `known_marketplaces.json` and `installed_plugins.json` under `sandbox.home` in the observed shapes, `.git/hooks/pre-push` carrying pre-commit's ID line → exit 0 and the only `manual` row is `quality-command`. New `test_unreadable_manual_state_is_printed` parametrized `secret-403` / `plugin-malformed` (`known_marketplaces.json` = `not json`) / `project-read` (with `--confirm`, the fault set before the run so it hits the post-write read) → exit 0, and the `review-secret` / `plugin-channel` row, or each of the three `project-*` rows, carries `(cannot read: `
- [x] 1.3 Run `agent-process check_red "tests/publisher/test_init_remote.py::test_manual_actions_are_printed[--dry-run]" "tests/publisher/test_init_remote.py::test_manual_actions_are_printed[--confirm]" "tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted[--dry-run]" "tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted[--confirm]" "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[secret-403]" "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[plugin-malformed]" "tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed[project-read]"` and verify each fails in its body. Commit as `test(distribution): manual rows follow observed state`

## 2. Installer

- [x] 2.1 `skills/agent-process/scripts/init.py` (D1): `_run` classifies and prints the manual rows last — after `_perform` on `--confirm`, after the plan otherwise — from a fresh guarded `gh repo view` read (D2; not `_repository`/`_gh_json`, which raise). Verify `python -m pytest tests/publisher/test_init_remote.py -q -k "manual_actions"` passes for `--confirm`
- [x] 2.2 Reads and conditions (D2–D4): `review-secret` from `gh secret list`, `project-*` from one GraphQL read of the linked Project and the template, `plugin-channel` from the two files under `ctx.home`, `pre-push` from `git config --get core.hooksPath` and the `--git-path hooks/pre-push` file; each failure is caught into `(cannot read: <reason>)`, never an `InstallError`. The module docstring's `manual` paragraph says the rows are read after the writes and printed only while outstanding. Verify `python -m pytest tests/publisher/test_init.py tests/publisher/test_init_remote.py tests/publisher/test_init_config.py tests/publisher/test_init_conflicts.py -q` passes
- [x] 2.3 `skills/agent-process/SKILL.md` Install: step 3 has the person do the `review-secret` row when the dry-run prints it; step 4's rows are the `manual` rows the confirmed run prints. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` passes. Commit as `fix(distribution): init prints only outstanding manual rows`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [x] 4.1 With a clean worktree, run `agent-process archive_change manual-rows-from-state`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: manual-rows-from-state" --body-file <report>`. The report references the tracking issue plainly, never with `Closes` (#269), and carries the scenario → test map and the observations of proposal — Why
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Observed done → `tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted`
- `distribution` / Unreadable state → `tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed`
- `distribution` / Manual actions → `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`
- `distribution` / Review prerequisites → `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed`
- `distribution` / Channel render → `tests/publisher/test_plugin.py::test_marketplace_follows_stable`
- `distribution` / Machine channel step → `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`
- `distribution` / Consumer render → `tests/publisher/test_init_config.py::test_pre_commit_block_references_the_hook`
- `distribution` / Consumer file without the block → `tests/publisher/test_init_conflicts.py::test_conflict_fails_closed[pre-commit-without-block]`
- `distribution` / Per-clone row → `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`
