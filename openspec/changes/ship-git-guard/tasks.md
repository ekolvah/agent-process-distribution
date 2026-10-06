## 0. Delivery start

- [x] 0.1 Run `agent-process start_change ship-git-guard --planner Claude --implementer Claude` for tracking issue 312. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/ship-git-guard`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_git_guard.py`, driving only the CLI (no module-level `load_script`, which would fail collection while the script is absent): run `[sys.executable, SKILL_SCRIPTS / "git_guard.py", "pre-bash"]` with a `{"tool_input": {"command": ...}}` payload on stdin and `encoding="utf-8"`. Tests:
  - `test_guarded_command_is_denied_with_the_alternative`, parametrized over the product of the base commands (`gh pr merge 5 --squash`, `gh repo delete x --yes`, `git push origin main`, `git push origin HEAD:main`, `git push origin x:refs/heads/main`, `git push --force`, `git push -fu origin b`, `git push --force-with-lease`, `git push --force-with-lease=main:abc origin b`, `git push --force-if-includes`, `git push origin +b`, `git push --no-verify`, `git commit --no-verify -m x`, `git commit -nm x`, `git reset --hard HEAD~1`, `git branch -D b`, `git branch --delete --force b`), each paired with a word of its D4 reason (`person merges`, `PR`, `commit on top`, `hook reports`, `stash`, `branch -d`), and the forms: alone, `cd x && <cmd>`, `sh -c '<cmd>'`, `timeout 5 <cmd>`, and for `git` commands `git -C . <rest>`, `git -c a=b <rest>`, `git --git-dir=.git <rest>`. Each exits 0 with `permissionDecision == "deny"` and the word in `permissionDecisionReason` (spec *Guarded command in an adopted consumer*, design D3);
  - `test_ordinary_command_is_silent`, parametrized over the spec's list (the unparseable one: `echo 'x`) plus `git push -n origin b`, `git branch -d -- -D`, `echo "gh pr merge"`, a payload without `tool_input`, and an empty stdin: exit 0, empty stdout and stderr (spec *Ordinary git command*);
  - `test_unparsed_git_command_is_a_visible_hook_error`: `git commit -F - <<'EOF'\ndon't\nEOF` exits 1, stdout empty, `not checked` on stderr (spec *Unparsed git command*, design D6);
  - `test_unknown_subcommand_is_a_visible_non_blocking_error`: no argument and `pre-read` each exit 1 with `usage` on stderr (design D1);
  - `test_no_static_deny_shadows_the_guard`: no `permissions.deny` pattern of `.claude/settings.json` matches `Bash(git push`, `Bash(git commit`, `Bash(git reset`, `Bash(git branch`, `Bash(gh pr merge` or `Bash(gh repo delete`; `Bash(sleep:*)` stays (spec *Repository settings carry no guard deny*)
- [x] 1.2 In `tests/publisher/test_plugin.py`, add `test_plugin_hooks_guard_git_in_an_adopted_repository` (spec *Guarded command in an adopted consumer*): a temporary project with an empty `.github/workflows/agent-process.yml`; exactly one `PreToolUse` `Bash` hook carries `git_guard`, and it shares the group and the gate of the `navigation_policy` hook (design D5); run through `_run_plugin_hook` with `gh pr merge 5`: exit 0, deny, reason contains `person merges`. In `test_plugin_hooks_deny_navigation_in_an_adopted_repository`, select hooks with `"navigation_policy" in command`, since a second `Bash` hook would otherwise be fed `cat README.md` and assert a deny it does not give. In `test_plugin_hooks_are_silent_outside_an_adopted_repository`, feed the `git_guard` command a guarded payload (`gh pr merge 5`), so the gate is what keeps it silent
- [x] 1.3 Run `agent-process check_red tests/publisher/test_git_guard.py tests/publisher/test_plugin.py::test_plugin_hooks_guard_git_in_an_adopted_repository`. Verify that each fails in its body: no script; no `git_guard` hook in `hooks/hooks.json`; the settings still carry the deny block. Commit as `test(distribution): the plugin ships the git guard`

## 2. Guard into the package

- [x] 2.1 In `skills/agent-process/scripts/navigation_policy.py`, extract `first_stage_verdict(command, rule)` from `_hint`/`_stage_hint` (design D2); the navigation verdict becomes a call with its rule. Verify that `python -m pytest tests/publisher/test_navigation_policy.py tests/agent_process/test_doc_headers.py -q` passes unchanged. Commit as `refactor(distribution): navigation_policy exposes its stage walker`
- [ ] 2.2 Add `skills/agent-process/scripts/git_guard.py` (design D1, D3, D4, D6): the module docstring states the problem (#312), that it is a guardrail and not a boundary (#357), and why it is a hook rather than a deny list. Add `git_guard.py` to `MOVED_SCRIPTS` in `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`. Verify that every test of `tests/publisher/test_git_guard.py` except `test_no_static_deny_shadows_the_guard` passes. Commit as `feat(distribution): git_guard denies merge and irreversible git commands`

## 3. Wiring

- [ ] 3.1 Add the guard hook of design D5 to the `PreToolUse` `Bash` group of `hooks/hooks.json`, and remove from `.claude/settings.json` every deny entry except `Bash(sleep:*)` (design D7). Verify that the group-1 targets and `python -m pytest tests/publisher -q` pass. Commit as `feat(distribution): the plugin ships the git guard, gated on adoption`

## 4. Documentation

- [ ] 4.1 In `skills/agent-process/SKILL.md` Install, name the guard and what it denies (merge, push to `main`, force, `--no-verify`, `reset --hard`, `branch -D`, `repo delete`) in the existing sentence on the plugin's navigation hooks, adding no other clause (design D8). Verify that `python -m pytest tests/publisher/test_plugin.py -q` passes. Commit as `docs(distribution): Install names the git guard`

## 5. Verify

- [ ] 5.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 5.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 6. Deliver

- [ ] 6.1 With a clean worktree, run `agent-process archive_change ship-git-guard`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: ship-git-guard" --body-file <report>`. The report references the tracking issue plainly (#312), never with `Closes`, and carries the scenario → test map, the identity follow-up (#357) and the consumer follow-up (kinozal_scraper deletes its deny block)
- [ ] 6.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `distribution` / Guarded command in an adopted consumer → `tests/publisher/test_plugin.py::test_plugin_hooks_guard_git_in_an_adopted_repository`, `tests/publisher/test_git_guard.py::test_guarded_command_is_denied_with_the_alternative`
- `distribution` / Ordinary git command → `tests/publisher/test_git_guard.py::test_ordinary_command_is_silent`
- `distribution` / Unparsed git command → `tests/publisher/test_git_guard.py::test_unparsed_git_command_is_a_visible_hook_error`
- `distribution` / Repository settings carry no guard deny → `tests/publisher/test_git_guard.py::test_no_static_deny_shadows_the_guard`
- `distribution` / Unadopted repository (existing) → `tests/publisher/test_plugin.py::test_plugin_hooks_are_silent_outside_an_adopted_repository`, which gets a guarded payload in 1.2
