## 0. Delivery start

- [x] 0.1 Run `agent-process start_change guard-unwraps-clustered-shell-flags --planner Claude --implementer Claude` for tracking issue 366. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/guard-unwraps-clustered-shell-flags`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_git_guard.py` add `test_clustered_shell_flag_is_unwrapped`, parametrized over every `GUARDED` command under `bash -lc`, `sh -ec` and `bash -c -e` (the command `shlex.quote`d): assert the call is denied and the reason carries the command's word, as `test_guarded_command_is_denied_with_the_alternative` does (D1, D2). In `_forms` add `bash --rcfile /dev/null -c {quoted}` and `bash -o pipefail -c {quoted}`: both pass on `main`, so they are preservation rows of the existing test, not RED rows (D1)
- [x] 1.2 In `tests/publisher/test_navigation_policy.py` add `test_clustered_shell_flag_is_unwrapped`, parametrized over `bash -lc "cat README.md"`, `sh -ec "cat file"` and `bash -c -e "grep -rn foo src/"`: assert `navigation_hint` is not None (D1, D2)
- [x] 1.3 Run `agent-process check_red tests/publisher/test_git_guard.py::test_clustered_shell_flag_is_unwrapped tests/publisher/test_navigation_policy.py::test_clustered_shell_flag_is_unwrapped`. Verify that it prints `RED: 54 failed` and exits 0. Commit as `test(distribution): a clustered shell -c hides the inner command`

## 2. Walker

- [x] 2.1 In `navigation_policy._stage_verdict` find the first token of `tokens[1:]` for which `re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", token)` holds (D1) and take as the command string the first later token that starts with neither `-` nor `+`, else `""` (D2); update the comment to name a clustered `-c`. Verify that `python -m pytest tests/publisher/test_git_guard.py tests/publisher/test_navigation_policy.py tests/publisher/test_plugin.py -q` passes. Commit as `fix(distribution): unwrap a clustered shell -c in the guard and navigation policy`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change guard-unwraps-clustered-shell-flags`. Verify that it archives the deltas into `openspec/specs/distribution/spec.md` and `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: guard-unwraps-clustered-shell-flags" --body-file <report>`. The report references the tracking issue plainly (#366), never with `Closes`, and carries the scenario → test map and the residual of design Non-Goals (a value option between the `c` cluster and the command string): it has no catcher beyond the default-branch ruleset and is accepted because the guard is a guardrail against agent error, not a security boundary (design Risks)
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Guarded command in an adopted consumer → `tests/publisher/test_git_guard.py::test_guarded_command_is_denied_with_the_alternative`, `tests/publisher/test_git_guard.py::test_clustered_shell_flag_is_unwrapped`, `tests/publisher/test_plugin.py::test_plugin_hooks_guard_git_in_an_adopted_repository`
- `distribution` / Ordinary git command → `tests/publisher/test_git_guard.py::test_ordinary_command_is_silent`
- `distribution` / Unparsed git command → `tests/publisher/test_git_guard.py::test_unparsed_git_command_is_a_visible_hook_error`
- `distribution` / Repository settings carry no guard deny → `tests/publisher/test_git_guard.py::test_no_static_deny_shadows_the_guard`
- `implementation` / Lint error → `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`
- `implementation` / Shell navigation → `tests/publisher/test_navigation_policy.py::test_a_denied_stage_is_found_anywhere_in_a_compound_command`, `tests/publisher/test_navigation_policy.py::test_clustered_shell_flag_is_unwrapped`
