## 0. Delivery start

- [x] 0.1 Run `agent-process start_change edit-time-lint-pre-commit --planner Claude --implementer Claude` for tracking issue 321. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/edit-time-lint-pre-commit`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_edit_lint.py`, driving only the CLI (`[sys.executable, SKILL_SCRIPTS / "edit_lint.py", <subcommand>]`, payload on stdin, `encoding="utf-8"`). A helper builds a temporary git repository with `a.py` and a `.pre-commit-config.yaml` of local hooks (`language: unsupported`, the interpreter quoted in `entry` as `tests/publisher/conftest.py` does), and runs the script with that repository as `cwd`. Tests:
  - `test_commit_stage_finding_reaches_the_agent`: a `stages: [pre-commit]` hook whose entry prints `finding:` and its arguments and exits 1; an `Edit` payload for `a.py` exits 2 with stderr containing `finding:` and `a.py` (spec *Commit-stage finding*);
  - `test_only_pre_push_hooks_run_nothing`: `default_install_hook_types: [pre-push]` and one `stages: [pre-push]` hook that writes a file `ran`; the script exits 0 with empty stdout and stderr, and `ran` does not exist (spec *Only pre-push hooks declared*);
  - `test_pre_commit_that_cannot_run_is_visible`, parametrized `no-pre-commit` (`PATH` set to an empty temporary directory) and `no-config` (no `.pre-commit-config.yaml`): exit 2; stderr contains `pre-commit` and `not active` for the first, `.pre-commit-config.yaml` for the second (spec *pre-commit missing*, *Linter cannot run*; design D1);
  - `test_payload_without_path_is_silent`, parametrized over empty stdin, `not json`, `{}` and `{"tool_input": {}}`: exit 0 with empty stdout and stderr;
  - `test_unknown_subcommand_prints_usage`: no argument and `on-edit` each exit 2 with `usage` on stderr.
- [x] 1.2 In `tests/publisher/test_plugin.py`, add `test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository` (spec *Commit-stage finding*, implementation *Lint error*): a temporary git repository with an empty `.github/workflows/agent-process.yml` and the failing commit-stage hook of 1.1; exactly one plugin hook command contains `edit_lint`, it sits in the `PostToolUse` group with matcher `Edit|Write`, beside the `memory_checkpoint` hook, and its hook object has `timeout` 120 (design D2); run through `_run_plugin_hook` with an `Edit` payload for `a.py`, it exits 2 with the hook's output on stderr
- [x] 1.3 In `tests/publisher/test_plugin.py`, add `test_publisher_lints_at_edit_time` (spec *This repository's edit-time lint*): this repository's `.pre-commit-config.yaml` has a repository `https://github.com/astral-sh/ruff-pre-commit` whose hooks are `ruff-check` and `ruff-format`, each with `stages == ["pre-commit"]`; `.agent-process/requirements-dev.in` has no `ruff` line; `.claude/settings.json` has no `hooks.PostToolUse` (also spec *Repository hook carries no memory check*). Loosen `test_publisher_pre_push_runs_the_entry` to assert that the `local` repository entry is unchanged and `default_install_hook_types == ["pre-push"]`, instead of the whole `repos` list
- [x] 1.4 In `tests/agent_process/test_ci_check.py`, add `test_lint_runs_the_commit_stage_hooks` (implementation *Edit-time check in the gate*): a temporary git repository, `monkeypatch.chdir`, with a `.pre-commit-config.yaml` of one local `stages: [pre-commit]` hook that prints `finding:` and exits 1 and one `stages: [pre-push]` hook that writes `ran`; `ci_check.check_lint()` raises `SystemExit`, the captured stdout contains `finding:`, and `ran` does not exist
- [x] 1.5 Run `agent-process check_red tests/publisher/test_edit_lint.py tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository tests/publisher/test_plugin.py::test_publisher_lints_at_edit_time tests/agent_process/test_ci_check.py::test_lint_runs_the_commit_stage_hooks`. Verify that each fails in its body: no script (stderr lacks the expected text, silent payloads exit 2); no `edit_lint` hook; no ruff-pre-commit repository; `check_lint` calls ruff, not the config's hook. Commit as `test(distribution): the plugin ships edit-time lint`

## 2. Script into the package

- [x] 2.1 Add `skills/agent-process/scripts/edit_lint.py` (design D1): the module docstring states the problem (#321) and that the project's pre-commit config, not the plugin, chooses the linters. Add `edit_lint.py` to `MOVED_SCRIPTS` in `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`. Verify that `python -m pytest tests/publisher/test_edit_lint.py -q` passes. Commit as `feat(distribution): edit_lint runs the project's commit-stage pre-commit hooks`

## 3. Plugin hook

- [x] 3.1 Add the hook object of design D2 to the existing `PostToolUse` `Edit|Write` group of `hooks/hooks.json`. In `test_plugin_hooks_remind_on_memory_write_in_an_adopted_repository`, select the `Edit|Write` command that contains `memory_checkpoint` instead of asserting a single one. Verify that `python -m pytest tests/publisher/test_plugin.py -q` passes, including `test_plugin_hooks_are_silent_outside_an_adopted_repository` over the new command. Commit as `feat(distribution): the plugin ships edit-time lint, gated on adoption`

## 4. One declaration of ruff

- [x] 4.1 Add the ruff-pre-commit repository of design D4 to `.pre-commit-config.yaml`, before the `local` one. Replace `check_format` and `check_lint` of `.agent-process/scripts/ci_check.py` with the one `check_lint` of design D5 and drop `format` from `CHECKS`. Remove `ruff` from `.agent-process/requirements-dev.in` and `.agent-process/requirements-dev.txt`. In `tests/agent_process/test_ci_check.py`, delete `test_bare_format_pass_excludes_the_process_paths` and `test_bare_lint_pass_excludes_the_process_paths`, and make `_process_repo` copy this repository's `.pre-commit-config.yaml` beside the process `pyproject.toml`. Verify that `python -m pytest tests/agent_process/test_ci_check.py tests/agent_process/test_ruff_silence_rules.py -q` passes (the `C901` and `RUF100` tests included), that `python .agent-process/scripts/ci_check.py --only lint` exits 0, and that `python .agent-process/scripts/ci_check.py --list` prints no `format`. Commit as `refactor(implementation): ci_check lints through the pre-commit config`

## 5. Drop the bespoke hook

- [x] 5.1 Delete `.agent-process/scripts/hooks.py`, `tests/publisher/test_hooks.py` and the `PostToolUse` entry of `.claude/settings.json`; drop the `test_hooks.py` sentence from the docstring of `tests/agent_process/test_delivery_gate_wiring.py` (design D6). Verify that `git grep -n "hooks.py on-edit\|test_hooks.py" -- . ':!openspec/changes'` prints only `.agent-process/docs/adr/0021-the-end-of-an-agent-turn-is-a-gated-event.md` (superseded, its history stays) and that `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_navigation_policy.py tests/agent_process/test_delivery_gate_wiring.py -q` passes. Commit as `refactor(distribution): this repository lints through its pre-commit config`

## 6. Documentation

- [x] 6.1 In `skills/agent-process/SKILL.md` Install, add the edit-time lint sentence of design D7 after the memory checkpoint. Add `.agent-process/docs/adr/0034-edit-time-lint-runs-the-projects-pre-commit-config.md` (MADR, `status: "accepted"`) with *Native alternatives considered* and *Deletion condition* (design D7). Verify that `python -m pytest tests/publisher/test_plugin.py tests/agent_process/test_adr_records.py tests/agent_process/test_doc_links.py -q` passes. Commit as `docs(distribution): edit-time lint in Install and ADR 0034`

## 7. Verify

- [x] 7.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 7.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 8. Deliver

- [x] 8.1 With a clean worktree, run `agent-process archive_change edit-time-lint-pre-commit`. Verify that it archives the deltas into `openspec/specs/distribution/spec.md` and `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 8.2 Run `gh pr create --title "feat: edit-time-lint-pre-commit" --body-file <report>`. The report references the tracking issue plainly (#321), never with `Closes`, and carries the scenario → test map, the Non-Goals of the design (no git `pre-commit` hook, consumers' gates) and the consumer follow-up (ekolvah/kinozal_scraper#614)
- [ ] 8.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 8.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Commit-stage finding → `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`, `tests/publisher/test_edit_lint.py::test_commit_stage_finding_reaches_the_agent`
- `distribution` / Only pre-push hooks declared → `tests/publisher/test_edit_lint.py::test_only_pre_push_hooks_run_nothing`
- `distribution` / pre-commit missing → `tests/publisher/test_edit_lint.py::test_pre_commit_that_cannot_run_is_visible`
- `distribution` / This repository's edit-time lint → `tests/publisher/test_plugin.py::test_publisher_lints_at_edit_time`
- `distribution` / Memory write in an adopted consumer (modified) → `tests/publisher/test_plugin.py::test_plugin_hooks_remind_on_memory_write_in_an_adopted_repository`, `tests/publisher/test_memory_checkpoint.py::test_memory_write_is_flagged`
- `distribution` / Write outside auto-memory (modified) → `tests/publisher/test_memory_checkpoint.py::test_writes_outside_memory_are_silent`
- `distribution` / Repository hook carries no memory check (modified) → `tests/publisher/test_plugin.py::test_publisher_lints_at_edit_time` (its `PostToolUse` assertion); `tests/publisher/test_hooks.py::test_memory_write_is_not_checked_here` is deleted with `hooks.py` in 5.1
- `distribution` / Unadopted repository (existing) → `tests/publisher/test_plugin.py::test_plugin_hooks_are_silent_outside_an_adopted_repository`, which runs the new command in 3.1
- `distribution` / This repository's push (existing) → `tests/publisher/test_plugin.py::test_publisher_pre_push_runs_the_entry`, loosened in 1.3
- `implementation` / Push (unchanged text) → `tests/publisher/test_plugin.py::test_publisher_pre_push_runs_the_entry`, `tests/publisher/test_quality.py::test_hook_repository_runs_at_pre_push`
- `implementation` / Edit-time check in the gate → `tests/agent_process/test_ci_check.py::test_lint_runs_the_commit_stage_hooks`
- `implementation` / Function over the complexity limit, Stale baseline entry (existing) → `tests/agent_process/test_ci_check.py::test_function_over_complexity_limit_fails_lint`, `::test_stale_baseline_fails_lint`, now through the pre-commit config in 4.1
- `implementation` / Lint error → `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`
- `implementation` / Shell navigation (unchanged text) → `tests/publisher/test_plugin.py::test_plugin_hooks_deny_navigation_in_an_adopted_repository`
- `implementation` / Linter cannot run → `tests/publisher/test_edit_lint.py::test_pre_commit_that_cannot_run_is_visible`
