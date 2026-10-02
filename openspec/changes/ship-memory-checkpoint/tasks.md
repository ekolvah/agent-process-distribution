## 0. Delivery start

- [x] 0.1 Run `agent-process start_change ship-memory-checkpoint --planner Claude --implementer Claude` for tracking issue 313. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/ship-memory-checkpoint`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_memory_checkpoint.py`, driving only the CLI (no module-level `load_script`, which would fail collection while the script is absent): run it as `[sys.executable, SKILL_SCRIPTS / "memory_checkpoint.py", <subcommand>]` with the payload on stdin and `encoding="utf-8"`. Tests:
  - `test_memory_write_is_flagged`, parametrized over a POSIX path, a Windows path with backslashes, and `memory/MEMORY.md` at the directory root: `post-edit` exits 2, and stderr contains the path, `every session` and `repository`, and does not contain `machine` (design D4);
  - `test_writes_outside_memory_are_silent`, parametrized over `src/x.py`, `.claude/rules/mindset.md`, `~/.claude/projects/slug/other/f.md`, a payload without `tool_input`, and an empty or malformed stdin: `post-edit` exits 0 with empty stdout and stderr (spec *Write outside auto-memory*);
  - `test_unknown_subcommand_prints_usage`: no argument and `on-edit` each exit 2 with `usage` on stderr (design D3).
- [x] 1.2 In `tests/publisher/test_plugin.py`, add `test_plugin_hooks_remind_on_memory_write_in_an_adopted_repository` (spec *Memory write in an adopted consumer*). Set up a temporary project with an empty `.github/workflows/agent-process.yml`. Exactly one plugin hook has event `PostToolUse` and matcher `Edit|Write`. Run through `_run_plugin_hook` with a `Write` payload under `<tmp>/.claude/projects/slug/memory/` in each separator style: it exits 2, and stderr names the file and contains `repository`. Leave `_denied_payloads` as the navigation map: `test_plugin_hooks_deny_navigation_in_an_adopted_repository` asserts at line 308 that its keys select exactly `Bash` and `Read`. Add a helper `_flagged_payloads(project)` that returns `{**_denied_payloads(project), "Edit|Write": <memory Write payload>}`. `test_plugin_hooks_are_silent_outside_an_adopted_repository` switches to it, so it feeds the new hook a payload the hook would flag
- [x] 1.3 In `tests/publisher/test_hooks.py`, replace `TestMemoryWriteGuard` with `test_memory_write_is_not_checked_here` (spec *Repository hook carries no memory check*). `run_on_edit` with a `Write` under `C:/Users/x/.claude/projects/slug/memory/f.md` returns `(0, "")`, with `ruff_runner=_never_called`. Keep the `.claude/rules/` and repository-path assertions of `test_repo_paths_not_memory` in this test. Remove `memory_write_signal` from the module's import list at line 29, because 2.2 deletes it from `hooks.py`
- [x] 1.4 Run `agent-process check_red tests/publisher/test_memory_checkpoint.py tests/publisher/test_plugin.py::test_plugin_hooks_remind_on_memory_write_in_an_adopted_repository tests/publisher/test_hooks.py::test_memory_write_is_not_checked_here`. Verify that each fails in its body: no script; no `PostToolUse` hook in `hooks/hooks.json`; `hooks.py` still exits 2. Commit as `test(distribution): the plugin ships the memory checkpoint`

## 2. Checkpoint into the package

- [x] 2.1 Add `skills/agent-process/scripts/memory_checkpoint.py` (design D1, D3, D4): the module docstring states the problem (#313) and why it reminds rather than blocks; the predicate moves from `hooks.py`; `main` takes `post-edit`. Add `memory_checkpoint.py` to `MOVED_SCRIPTS` in `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`. Verify that `python -m pytest tests/publisher/test_memory_checkpoint.py -q` passes
- [x] 2.2 Remove the memory branch from `.agent-process/scripts/hooks.py` (design D5); its docstring names the plugin's checkpoint. Verify that `python -m pytest tests/publisher/test_hooks.py -q` passes. Commit as `refactor(distribution): the memory checkpoint moves into the skill package`

## 3. Plugin hook

- [x] 3.1 Add the `PostToolUse` `Edit|Write` entry of design D2 to `hooks/hooks.json`. Verify that the three group-1 test targets and `python -m pytest tests/publisher -q` pass. Commit as `feat(distribution): the plugin ships the memory checkpoint, gated on adoption`

## 4. Documentation

- [x] 4.1 In `skills/agent-process/SKILL.md` Install, add the memory checkpoint to the sentence on the plugin's navigation hooks: after an edit under the agent's auto-memory directory, it asks whether every session and every person needs the fact, and if so to move it into the repository (design D6). Verify that `python -m pytest tests/publisher/test_plugin.py -q` passes. Commit as `docs(distribution): Install names the memory checkpoint`

## 5. Verify

- [x] 5.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 5.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 6. Deliver

- [ ] 6.1 With a clean worktree, run `agent-process archive_change ship-memory-checkpoint`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: ship-memory-checkpoint" --body-file <report>`. The report references the tracking issue plainly (#313), never with `Closes`, and carries the scenario → test map and the consumer follow-up (ekolvah/kinozal_scraper#614)
- [ ] 6.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Memory write in an adopted consumer → `tests/publisher/test_plugin.py::test_plugin_hooks_remind_on_memory_write_in_an_adopted_repository`, `tests/publisher/test_memory_checkpoint.py::test_memory_write_is_flagged`
- `distribution` / Write outside auto-memory → `tests/publisher/test_memory_checkpoint.py::test_writes_outside_memory_are_silent`
- `distribution` / Repository hook carries no memory check → `tests/publisher/test_hooks.py::test_memory_write_is_not_checked_here`
- `distribution` / Unadopted repository (existing) → `tests/publisher/test_plugin.py::test_plugin_hooks_are_silent_outside_an_adopted_repository`, which gets the memory payload in 1.2
