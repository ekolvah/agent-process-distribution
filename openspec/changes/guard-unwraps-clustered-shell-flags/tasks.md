## 0. Delivery start

- [x] 0.1 Run `agent-process start_change guard-unwraps-clustered-shell-flags --planner Claude --implementer Claude` for tracking issue 366. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/guard-unwraps-clustered-shell-flags`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_git_guard.py` add `test_clustered_shell_flag_is_unwrapped`, parametrized over every `GUARDED` command under `bash -lc`, `sh -ec` and `bash -c -e` (the command `shlex.quote`d): assert the call is denied and the reason carries the command's word, as `test_guarded_command_is_denied_with_the_alternative` does (D1, D2). In `_forms` add `bash --rcfile /dev/null -c {quoted}` and `bash -o pipefail -c {quoted}`: both pass on `main`, so they are preservation rows of the existing test, not RED rows (D1)
- [x] 1.2 In `tests/publisher/test_navigation_policy.py` add `test_clustered_shell_flag_is_unwrapped`, parametrized over `bash -lc "cat README.md"`, `sh -ec "cat file"` and `bash -c -e "grep -rn foo src/"`: assert `navigation_hint` is not None (D1, D2)
- [x] 1.3 Run `agent-process check_red tests/publisher/test_git_guard.py::test_clustered_shell_flag_is_unwrapped tests/publisher/test_navigation_policy.py::test_clustered_shell_flag_is_unwrapped`. Verify that it prints `RED: 54 failed` and exits 0. Commit as `test(distribution): a clustered shell -c hides the inner command`

## 2. Walker and navigation route

- [x] 2.1 In `navigation_policy._stage_verdict` find the first token of `tokens[1:]` for which `re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", token)` holds (D1) and take as the command string the first later token that starts with neither `-` nor `+`, else `""` (D2); update the comment to name a clustered `-c`. Verify that `python -m pytest tests/publisher/test_git_guard.py tests/publisher/test_navigation_policy.py tests/publisher/test_plugin.py -q` passes. Commit as `fix(distribution): unwrap a clustered shell -c in the guard and navigation policy`
- [ ] 2.2 RED for D3 and D5:
  - In `tests/publisher/test_plugin.py::test_plugin_hooks_deny_navigation_in_an_adopted_repository` assert that the plugin's `navigation_policy` hooks match `Read` only, and run only the `Read` payload through them; keep the `Bash` key of `_denied_payloads`, which `test_plugin_hooks_are_silent_outside_an_adopted_repository` falls back to.
  - Add `test_plugin_hooks_allow_shell_navigation_in_an_adopted_repository`: in an adopted directory run `cat README.md`, `grep -rn foo src/`, `find . -name '*.py'` and `sed -n 1,5p a.py` through every plugin `PreToolUse` `Bash` hook and assert that none outputs a deny.
  - In `tests/publisher/test_navigation_policy.py` add `test_unknown_subcommand_is_a_visible_non_blocking_error`, parametrized over `()` and `("pre-bash",)`, mirroring the `git_guard` test of that name: exit 1 and `usage` on stderr.
  - In `_forms` of `tests/publisher/test_git_guard.py` add `true; {command}` and `true | {command}`: they pass now and keep the separators covered once the walker moves (D4).

  Run `agent-process check_red tests/publisher/test_plugin.py::test_plugin_hooks_deny_navigation_in_an_adopted_repository tests/publisher/test_plugin.py::test_plugin_hooks_allow_shell_navigation_in_an_adopted_repository tests/publisher/test_navigation_policy.py::test_unknown_subcommand_is_a_visible_non_blocking_error`; verify that it prints `RED: 4 failed` and exits 0. Commit as `test(distribution): the plugin ships no Bash navigation hook`
- [ ] 2.3 Remove the route and move the walker:
  - Remove the `navigation_policy pre-bash` entry from `hooks/hooks.json` and, from `navigation_policy.py`, the `Bash` route of D3 with its `pre-bash` subcommand; make `main` exit 1 with the usage for any argv but `pre-read` (D5).
  - Rewrite for the `Read` route alone the module docstring, the docstrings that cite `pre_bash_response` or `Bash`, and the Read denial's closing "Reading is budgeted like shell navigation."
  - Move the walker of D4 into `git_guard.py`, importing only `_deny` from `navigation_policy`.
  - In `tests/publisher/test_navigation_policy.py` delete the `Bash` route's tests (`test_filesystem_reads_are_denied_with_the_replacement_named`, `test_pipe_stages_and_toolchain_stay_allowed`, `test_a_denied_stage_is_found_anywhere_in_a_compound_command`, `test_clustered_shell_flag_is_unwrapped`, `test_heredoc_write_is_routed_to_the_edit_tools`, `test_unparseable_command_fails_open`, the `pre_bash_response` tests of `TestClaudeAdapter`, `TestClaudeHookWiring::test_no_static_deny_shadows_the_hook`), narrow `test_pre_tool_use_subcommands_are_accepted` to `pre-read` and rewrite its fail-closed docstring, and rewrite the module docstring.
  - In `tests/publisher/test_plugin.py::test_plugin_hooks_guard_git_in_an_adopted_repository` take the adoption gate from the `Read` hook of `navigation_policy` instead of a `navigation_policy` hook in the `Bash` group.
  - In `tests/agent_process/test_doc_headers.py` update or drop the comment and registration that exist for the policy's `@dataclass`, which D3 removes.
  - In `skills/agent-process/SKILL.md` make the Claude harness bullet and the Install sentence name the read-budget hook on `Read` instead of navigation hooks on shell reads.

  Verify that `python -m pytest tests -q` passes. Commit as `fix(distribution): drop the navigation policy's Bash route`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change guard-unwraps-clustered-shell-flags`. Verify that it archives the deltas into `openspec/specs/distribution/spec.md` and `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 The PR is open (#372): run `gh pr edit 372 --body-file <report>`. The report references the tracking issue plainly (#366), never with `Closes`, and carries the measurement of the proposal's **Why**, the scenario → test map and the residual of design Non-Goals (a value option between the `c` cluster and the command string): it has no catcher beyond the default-branch ruleset and is accepted because the guard is a guardrail against agent error, not a security boundary (design Risks)
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Guarded command in an adopted consumer → `tests/publisher/test_git_guard.py::test_guarded_command_is_denied_with_the_alternative`, `tests/publisher/test_git_guard.py::test_clustered_shell_flag_is_unwrapped`, `tests/publisher/test_plugin.py::test_plugin_hooks_guard_git_in_an_adopted_repository`
- `distribution` / Ordinary git command → `tests/publisher/test_git_guard.py::test_ordinary_command_is_silent`
- `distribution` / Unparsed git command → `tests/publisher/test_git_guard.py::test_unparsed_git_command_is_a_visible_hook_error`
- `distribution` / Repository settings carry no guard deny → `tests/publisher/test_git_guard.py::test_no_static_deny_shadows_the_guard`
- `distribution` / Adopted consumer → `tests/publisher/test_plugin.py::test_plugin_hooks_deny_navigation_in_an_adopted_repository`
- `distribution` / Repository settings carry no navigation hook → `tests/publisher/test_plugin.py::test_publisher_settings_declare_no_navigation_hook`
- `implementation` / Lint error → `tests/publisher/test_plugin.py::test_plugin_hooks_lint_the_edited_file_in_an_adopted_repository`
- `implementation` / Shell navigation → `tests/publisher/test_plugin.py::test_plugin_hooks_allow_shell_navigation_in_an_adopted_repository`
- `implementation` / Whole-file read over the budget → `tests/publisher/test_navigation_policy.py::TestReadBudget::test_whole_file_read_over_threshold_is_denied`, `tests/publisher/test_navigation_policy.py::TestClaudeAdapter::test_read_denial_uses_the_documented_pretooluse_shape`
