## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py ship-only-distributed-paths --planner Claude --implementer Claude` for tracking issue 216. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/ship-only-distributed-paths`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_plugin.py` add `test_marketplace_fetches_only_the_package` (D1): the `sparsePaths` of the `agent-process-marketplace` source in `init._render_settings(init.VERSION)` and in this repository's `.claude/settings.json` both equal `[".claude-plugin", "agents", "commands", "skills/agent-process"]`; each entry exists in the repository; and every plugin component root the repository has at its top level (`commands`, `agents`, each directory `skills/<name>`, `hooks`, `output-styles`, `.mcp.json`, `.lsp.json`, and `.claude-plugin`) lies under an entry of both lists. In `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed` expect the same `sparsePaths` in the rendered source. Verify with the 1.3 run
- [x] 1.2 In `tests/publisher/test_init.py` add `test_confirm_leaves_the_user_profile_alone` (D2): a fresh `--confirm` exits 0 and `snapshot(sandbox.home)` is identical before and after. Rewrite `test_confirm_selects_release_before_composing`: the handed-off `init.py` (its `file ` line) lies outside `sandbox.home`, its release directory no longer exists after the run, `snapshot(sandbox.home)` is unchanged, a `clone` precedes the hand-off, no `npx` ran, and `snapshot(sandbox.root) == {}`. Verify with the 1.3 run
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_plugin.py::test_marketplace_fetches_only_the_package tests/publisher/test_init_remote.py::test_installed_footprint_is_closed tests/publisher/test_init.py::test_confirm_leaves_the_user_profile_alone tests/publisher/test_init.py::test_confirm_selects_release_before_composing` and verify every test fails in its body. Commit as `test(distribution): only the package reaches a consumer`

## 2. Marketplace (D1)

- [x] 2.1 Add `"sparsePaths": [".claude-plugin", "agents", "commands", "skills/agent-process"]` to the marketplace source of `skills/agent-process/templates/settings.json` and of `.claude/settings.json`; in `test_plugin.py::test_publisher_dogfoods_process` expect it. Verify `python -m pytest tests/publisher/test_plugin.py tests/publisher/test_init_remote.py tests/publisher/test_init_config.py -q` passes. Commit as `feat(distribution): the marketplace fetches only the package`

## 3. Installer (D2)

- [ ] 3.1 `init.py`: remove `_checkout`, `Context.checkout`, `_same_path` and the `checkout` step; `_run` clones the tag with `--depth 1` into a `tempfile.TemporaryDirectory` for any other version, in both modes, and `--confirm` hands off from it after printing `planned hand-off`; the same-version plan starts at `openspec`. Keep `Host.home`/`Context.home` as the injected boundary; verify `Path.home()` appears only in `main()`. Update the module docstring (no step 1, the confirm hand-off from a temporary clone). Verify `python -m pytest tests/publisher/test_init.py -q` passes
- [ ] 3.2 Tests follow the removed step: `init_harness.py` drops `Sandbox.checkout` and `checkout` from `LABELS`; `test_init.py::test_lifecycle` expects `{"hand-off": "planned"}` for a confirmed or retried upgrade and an unchanged `sandbox.home` in every case, `test_retry_after_each_write` keeps the `fresh` scenario only and `_final` drops `head`; `test_init_conflicts.py` drops the `checkout-*` cases and their helpers; the `~/.agent-process/` exemption comment of `test_plugin.py::test_package_paths_resolve_in_a_consumer` stays only if a package file still names that path. Verify `python -m pytest tests/publisher -q` passes. Commit as `feat(distribution): init keeps no process checkout`

## 4. Verify

- [ ] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py ship-only-distributed-paths`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: ship-only-distributed-paths" --body-file <report>`. The report names tracking issue 216 as a plain reference (never `Closes`), carries the scenario → test map, and names the migration: a machine that already knows the marketplace keeps its full clone until the marketplace is added again; an existing `~/.agent-process/distribution` is left unused
- [ ] 5.3 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Settings render → `tests/publisher/test_plugin.py::test_marketplace_fetches_only_the_package`; `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed`
- `distribution` / Confirmed upgrade → `tests/publisher/test_init.py::test_confirm_selects_release_before_composing`
- `distribution` / Confirmed install of the running release → `tests/publisher/test_init.py::test_confirm_leaves_the_user_profile_alone`
- `distribution` / Target the installer does not own → `tests/publisher/test_init_conflicts.py::test_conflict_fails_closed` (checkout cases removed, the rest unchanged)
