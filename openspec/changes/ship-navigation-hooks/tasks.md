## 0. Delivery start

- [x] 0.1 Run `agent-process start_change ship-navigation-hooks --planner Claude --implementer Claude` for tracking issue 310. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/ship-navigation-hooks`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py`, add `"hooks"` to `COMPONENT_ROOTS` (spec *Component roots*)
- [x] 1.2 In `tests/publisher/test_plugin.py`, add a helper that reads `hooks/hooks.json` through its `"hooks"` envelope and returns the `(event, matcher, command)` of every hook of every event, and a helper that runs one command with `sh -c` (as `_run_launcher` finds `sh`), `cwd` a temporary directory, env `CLAUDE_PROJECT_DIR` = that directory and `CLAUDE_PLUGIN_ROOT` = the repository root, the payload on stdin, `encoding="utf-8"`
- [x] 1.3 Add `test_plugin_hooks_deny_navigation_in_an_adopted_repository` (spec *Adopted consumer*): a temporary project with an empty `.github/workflows/agent-process.yml` and no `skills/`; the `Bash` command with payload `{"tool_input": {"command": "cat README.md"}}` and the `Read` command with a whole-file read of a file over `_READ_BUDGET_BYTES` in that project each exit 0 with a `hookSpecificOutput.permissionDecision` of `deny` whose reason names `Read` (resp. `offset`); exactly one hook per matcher `Bash` and `Read`
- [x] 1.4 Add `test_plugin_hooks_are_silent_outside_an_adopted_repository` (spec *Unadopted repository*): for every command of every event of `hooks/hooks.json` (assert at least the two PreToolUse ones), the same denied payloads in a temporary project without the marker exit 0 with empty stdout
- [x] 1.5 Add `test_publisher_settings_declare_no_navigation_hook` (spec *Repository settings carry no navigation hook*): no `hooks.PreToolUse` entry of `.claude/settings.json` has matcher `Bash` or `Read`
- [x] 1.6 Run `agent-process check_red tests/publisher/test_plugin.py::test_plugin_component_roots_are_closed tests/publisher/test_plugin.py::test_plugin_hooks_deny_navigation_in_an_adopted_repository tests/publisher/test_plugin.py::test_plugin_hooks_are_silent_outside_an_adopted_repository tests/publisher/test_plugin.py::test_publisher_settings_declare_no_navigation_hook` and verify each fails in its body (`hooks` missing; no `hooks/hooks.json`; settings still wire `Bash`/`Read`). Commit as `test(distribution): the plugin ships gated navigation hooks`

## 2. Policy into the package

- [x] 2.1 `git mv .agent-process/scripts/navigation_policy.py skills/agent-process/scripts/navigation_policy.py`; move `pre_bash_response`, `pre_read_response` and their dispatch from `.agent-process/scripts/hooks.py` into it with a `main` taking `pre-bash|pre-read` (any other argument: usage on stderr, exit 2; otherwise the deny JSON or nothing, exit 0) (design D1). `hooks.py` keeps `on-edit` only; update its docstring and usage. Add `navigation_policy.py` to `MOVED_SCRIPTS` in `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`
- [x] 2.2 `git mv tests/agent_process/test_navigation_policy.py tests/publisher/test_navigation_policy.py`; load the module from `skills/agent-process/scripts/` the way the other publisher tests load skill scripts; delete `TestClaudeHookWiring`'s two `test_pretooluse_hook_is_wired_for_*` tests (replaced by 1.3–1.5), keep its two shadowing tests. Move `test_pre_read_is_an_accepted_subcommand` from `tests/publisher/test_hooks.py` into it, running `navigation_policy.py pre-read`, and add `pre-bash` to it. Re-point the import in `tests/agent_process/test_doc_headers.py`. Verify `python -m pytest tests/publisher -q` and `python -m pytest -c .agent-process/pyproject.toml tests/agent_process -q` pass but for the RED tests of group 1. Commit as `refactor(distribution): navigation policy moves into the skill package`

## 3. Plugin hooks

- [ ] 3.1 Add `hooks/hooks.json` with PreToolUse matchers `Bash` and `Read`, timeout 10, commands as design D2 with the gate of D3
- [ ] 3.2 Add `ROOT / "hooks"` to the roots of `_package_text_files` in `tests/publisher/test_plugin.py`, so `test_package_paths_resolve_in_a_consumer` covers `hooks/hooks.json`
- [ ] 3.3 Remove the PreToolUse `Bash` and `Read` entries from `.claude/settings.json` (design D4); keep the PostToolUse `on-edit` entry
- [ ] 3.4 Verify the four group-1 tests and `python -m pytest tests/publisher -q` pass. Commit as `feat(distribution): the plugin ships the navigation hooks, gated on adoption`

## 4. Documentation

- [ ] 4.1 In `skills/agent-process/SKILL.md` Install, add the sentence of design D7 to the plugin paragraph. Verify `python -m pytest tests/publisher/test_plugin.py -q` passes. Commit as `docs(distribution): Install names the plugin's navigation hooks`

## 5. Verify

- [ ] 5.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 5.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 6. Deliver

- [ ] 6.1 With a clean worktree, run `agent-process archive_change ship-navigation-hooks`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: ship-navigation-hooks" --body-file <report>`. The report references the tracking issue plainly, never with `Closes`, and carries the scenario → test map, the consumer follow-up ekolvah/kinozal_scraper#612, and the revisit condition (anthropics/claude-code#75855)
- [ ] 6.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Component roots → `tests/publisher/test_plugin.py::test_plugin_component_roots_are_closed` (`COMPONENT_ROOTS` changed in 1.1)
- `distribution` / Settings render → `tests/publisher/test_plugin.py::test_marketplace_source_is_whole` (existing)
- `distribution` / Adopted consumer → `tests/publisher/test_plugin.py::test_plugin_hooks_deny_navigation_in_an_adopted_repository`
- `distribution` / Repository settings carry no navigation hook → `tests/publisher/test_plugin.py::test_publisher_settings_declare_no_navigation_hook`
- `distribution` / Unadopted repository → `tests/publisher/test_plugin.py::test_plugin_hooks_are_silent_outside_an_adopted_repository`
