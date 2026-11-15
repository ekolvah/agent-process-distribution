## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-sets-review-secret --planner Claude --implementer Claude` (tracking issue 516), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 Move `_no_token` (taking the token as a parameter) and `_line` from `tests/publisher/test_init_readings.py` into `tests/publisher/init_harness.py` as `no_token` and `line`, and use them there; verify `python -m pytest tests/publisher/test_init_readings.py -q` stays green
- [x] 1.2 Add `tests/publisher/test_init_review_secret.py` (module docstring names the requirement *The review secret is set from the machine's token*), over the `init_harness` sandbox with `sb.home / ".claude" / "agent-process-review-token"` holding `sk-ant-oat01-review-token-0123` plus a trailing newline (`# pragma: allowlist secret`): `test_secret_set_from_token_file` (confirmed run: `written review-secret` precedes `written onboarding-push`, `sandbox.github.secret_values == {"CLAUDE_CODE_OAUTH_TOKEN": <token stripped>}`, no `manual review-secret` row, `no_token` over output and commands); `test_secret_planned` (`--dry-run`: `planned review-secret`, no `secret set` command, no `manual review-secret` row, `no_token` over output and commands); `test_secret_already_set` (`secrets` holds the name, no token file: `unchanged review-secret`, no `secret set` command, no row); `test_secret_write_fails` (`faults["secret-set"] = "fail"`: exit 1, stderr names `review-secret`, no `git push` in the runner log)
- [x] 1.3 In `tests/publisher/test_init_remote.py` rewrite `test_review_prerequisites_are_printed` over both modes with no token file, plus `--dry-run` cases with a blank file and with the token path a directory: no `review-secret` transition, no `secret set` command, one row naming the secrets page, `claude setup-token`, `~/.claude/agent-process-review-token` and ending `(not found: ~/.claude/agent-process-review-token)`, or `(cannot read: ` for the directory; the `UNREADABLE` table's `secret-403` case also writes a token file and asserts no `review-secret` transition prints while the `review-secret` row still ends `(cannot read: …)` (a guard that already passes, run green in 2.1, not given to `check_red`)
- [x] 1.4 Run `agent-process check_red` on the tests of 1.2 and `test_review_prerequisites_are_printed`, verify each fails because `init` has no `review-secret` step and the row still names `gh secret set`, and commit RED with the group 1 ticks

## 2. Implementation

- [x] 2.1 In `skills/agent-process/scripts/manual.py` extract the token-file read of `_mcp_grafana` into a helper both use, add `REVIEW_TOKEN_FILE` and `review_token(t)` on it, and make the `review-secret` row print only while no step is planned, name the one-time file step, and append `(not found: …)` or `(cannot read: <file>: <reason>)` (design D1–D3); verify `python -m pytest tests/publisher/test_init_remote.py tests/publisher/test_init_readings.py -q` is green
- [x] 2.2 In `skills/agent-process/scripts/readings_setup.py` move `gh_step` to module level and let `steps` take the secret names; in `skills/agent-process/scripts/init.py` read the names once in `_run`, pass them to `readings_setup.steps` and to a `review-secret` step built with `gh_step`, placed between the Project steps and the `after` onboarding steps (design D2); update the docstring's step list and its sentences on the run's secret writes; verify `python -m pytest tests/publisher/test_init_review_secret.py tests/publisher/test_init.py -q` is green, then commit 2.1–2.2 with their ticks
- [x] 2.3 In `skills/agent-process/SKILL.md` Install, Prepare's second bullet becomes once per machine: run `claude setup-token` in your own terminal and save the printed token to `~/.claude/agent-process-review-token`, which keeps it out of the chat; step 3 becomes: when the dry-run prints the `review-secret` row, have the person save Prepare's token file and run the dry-run again before `--confirm`, so the first pushed head's `agent-review` runs with the secret. Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` is green
- [x] 2.4 Add `.agent-process/docs/adr/0049-init-sets-the-review-secret-from-a-machine-token-file.md` from `template.md` with design D1–D3 (including D3's catcher and recovery for a bad token), the alternatives and the risk; in ADR 0032 add under Consequences "Superseded by ADR 0049 on D2: `init` sets the secret from the machine's token file." Verify `grep -n "0049" .agent-process/docs/adr/0032-the-review-gate-is-installed-in-every-consumer.md` prints the line, then commit 2.3–2.4 with their ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change init-sets-review-secret`, then `gh pr create --title "feat: init-sets-review-secret" --body-file <report>`. The report names tracking issue 516 as a plain reference, carries the scenario-to-test map, states design **Risks** and names the principles it interacts with (goal 1, goal 3, §II, §IV, §VII)
- [ ] 4.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Secret set from the token file | `tests/publisher/test_init_review_secret.py::test_secret_set_from_token_file` |
| distribution / Secret planned | `tests/publisher/test_init_review_secret.py::test_secret_planned` |
| distribution / Review prerequisites | `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed` |
| distribution / Readings prerequisites | `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` (unchanged; its sandbox has no token file) |
| distribution / Secret already set | `tests/publisher/test_init_review_secret.py::test_secret_already_set` |
| distribution / Secret write fails | `tests/publisher/test_init_review_secret.py::test_secret_write_fails` |
