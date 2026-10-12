## 0. Delivery start

- [x] 0.1 Run `agent-process start_change install-admin-as-person --planner Claude --implementer Claude` for tracking issue 407. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/install-admin-as-person`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `test_a_clone_with_the_agent_identity` to `tests/publisher/test_agent_identity.py`: with `GH_TOKEN` and `GITHUB_TOKEN` set by `monkeypatch.setenv`, the default `gh` of `main` (`main.__kwdefaults__["gh"]`) of both `activate_protection` and `agent_identity` runs `[sys.executable, "-c", <print both variables>]` and sees neither; `agent_identity.bot_gh("<bot token>")` running the same probe sees `GH_TOKEN` equal to the bot token. Run `agent-process check_red tests/publisher/test_agent_identity.py::test_a_clone_with_the_agent_identity` and commit RED with the Group 1 ticks

## 2. Person runner (design D1, D2)

- [x] 2.1 In `skills/agent-process/scripts/set_status.py`, add `person_gh` beside `run_gh`: `run_gh` with the process environment minus `GH_TOKEN` and `GITHUB_TOKEN`. Make it the default `gh` of `activate_protection.main` and `agent_identity.main`, and say in each docstring that the person-side `gh` calls run as the stored active account. Verify with `python -m pytest tests/publisher/test_agent_identity.py tests/publisher/test_activate_protection.py tests/publisher/test_set_status.py`
- [x] 2.2 Live, from this session (its `GH_TOKEN` is the bot's): run `python skills/agent-process/scripts/agent_identity.py --bot ekolvah-agent --dry-run` and `python skills/agent-process/scripts/activate_protection.py --pr 405 --dry-run`. Verify that every transition and the ruleset print `unchanged`, and record both outputs in this tick. Commit
  - 2026-10-12, session `gh api user` → `ekolvah-agent`. `activate_protection --pr 405 --dry-run`: `unchanged 23732345`, `classic: none (not written)`, rc 0. `agent_identity --bot ekolvah-agent --dry-run` from the worktree planned only `settings` (the git-ignored `.claude/settings.local.json` lives in the main clone, not the worktree); the same code with `root` = the main clone: `unchanged` collaborator, project, settings, git, `ruleset: 24939338`, rc 0
- [x] 2.3 Add `"ask": ["Bash(*activate_protection* --confirm*)", "Bash(*agent_identity* --confirm*)"]` to `permissions` in `.claude/settings.json` (design D4), writing the file in `init`'s `_json_text` form. Verify with `python -c "import json,pathlib; t=pathlib.Path('.claude/settings.json').read_text(encoding='utf-8'); d=json.loads(t); assert t == json.dumps(d, indent=2, ensure_ascii=False) + '\n'; print(d['permissions'])"` and `python -m pytest tests/publisher/test_init.py`. Commit

## 3. ADR (design D3)

- [x] 3.1 Add D6 to `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md`: Install's admin steps call `gh` as the person's stored account by dropping `GH_TOKEN` and `GITHUB_TOKEN`, the limit its Consequences accept, used on purpose behind `--dry-run` and the person's yes to `--confirm`; the bot-side calls of `agent_identity` keep the bot's token; in this repository `--confirm` also asks the person (design D4). Name `tests/publisher/test_agent_identity.py::test_a_clone_with_the_agent_identity` under Confirmation. Verify with `git diff --stat` that only the ADR changed. Commit

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument, and commit its edits or record `no edits` with the skipped findings in this tick
- [ ] 4.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 4.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [ ] 5.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change install-admin-as-person`. Verify that it merges the delta into `openspec/specs/distribution/spec.md`, archives, commits and pushes the branch
- [ ] 5.2 Run `gh pr create --title "fix: install-admin-as-person" --body-file <report>`. The report references tracking issue #407 plainly, never with `Closes`, and carries the scenario → test map
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change. The person merges it

## Scenario → test map

| Scenario | Test |
|---|---|
| A clone with the agent's identity (`distribution`) | `tests/publisher/test_agent_identity.py::test_a_clone_with_the_agent_identity` |
