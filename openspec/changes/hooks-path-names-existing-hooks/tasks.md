## 0. Delivery start

- [x] 0.1 Run `agent-process start_change hooks-path-names-existing-hooks --planner Claude --implementer Claude` (tracking issue 472), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/test_init_remote.py` add `test_pre_push_names_existing_hooks`, parametrized `--dry-run` / `--confirm`: `git config core.hooksPath .hooks` in the sandbox, `.hooks/commit-msg` and `.hooks/pre-push.sample` written. The run exits 0, prints no `pre-push` transition, leaves the `.hooks` listing unchanged and `_hook(sandbox)` absent, and its one `manual pre-push` row contains `str(sandbox.root / ".hooks")`, `commit-msg`, `stops running`, `.pre-commit-config.yaml`, `repo: local`, `git config --unset-all core.hooksPath` and `pre-commit install --hook-type pre-push`, and not `pre-push.sample`. In `test_pre_push_blocked_is_manual` also assert `"repo: local" not in row`
- [x] 1.2 In `tests/publisher/test_skill_check.py` give `_clone` a `hooks: tuple[str, ...] = ()` argument that writes those files into `project / ".hooks"`, and add `test_pre_push_names_existing_hooks`: `_clone(tmp_path, hook=True, hooks_path=True, hooks=("commit-msg",))` with `BLOCK`; both texts contain `PRE_PUSH_MARKER`, `str(project / ".hooks")`, `commit-msg`, `stops running`, `.pre-commit-config.yaml` and `repo: local`. In the `hooks-path` case of `test_pre_push_missing_is_marked` also assert `"repo: local" not in text`
- [x] 1.3 Run `agent-process check_red tests/publisher/test_init_remote.py::test_pre_push_names_existing_hooks tests/publisher/test_skill_check.py::test_pre_push_names_existing_hooks` and commit RED with these ticks

## 2. Reason names the hooks

- [x] 2.1 `skills/agent-process/scripts/manual.py` (design D1–D3): in `pre_push`, with `core.hooksPath` set, list `hook.parent` without `*.sample` names (a missing directory gives none, another `OSError` raises `Unreadable`) and return the reworded reason when any remain; the `PrePush.blocked` docstring stays true. Verify `python -m pytest tests/publisher/test_init_remote.py -q` is green
- [x] 2.2 `skills/agent-process/templates/skill_check.py` (design D1, D2, D4): in `_pre_push`, read `--git-path hooks/pre-push` before the `core.hooksPath` branch and return the same reworded reason from `hook.parent`. Verify `python -m pytest tests/publisher/test_skill_check.py tests/publisher/test_plugin.py -q` is green, then commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change hooks-path-names-existing-hooks`, then `gh pr create --title "fix: hooks-path-names-existing-hooks" --body-file <report>`. The report names tracking issue 472 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §I, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Consumer render | n/a: unchanged by this change |
| distribution / Consumer file without the block | n/a: unchanged by this change |
| distribution / Hook installed in this clone | n/a: unchanged by this change |
| distribution / Install leaves no hook | n/a: unchanged by this change |
| distribution / Hook missing where nothing else is planned | n/a: unchanged by this change |
| distribution / Per-clone row | `tests/publisher/test_init_remote.py::test_pre_push_blocked_is_manual` (gains the `repo: local` absence) |
| distribution / Per-clone row over existing hooks | `tests/publisher/test_init_remote.py::test_pre_push_names_existing_hooks` |
| distribution / Hook missing | `tests/publisher/test_skill_check.py::test_pre_push_missing_is_marked` (gains the `repo: local` absence) |
| distribution / Hook missing over existing hooks | `tests/publisher/test_skill_check.py::test_pre_push_names_existing_hooks` |
| distribution / Hook installed or not rendered | n/a: unchanged by this change |
| distribution / Hook state unreadable | n/a: unchanged by this change |
