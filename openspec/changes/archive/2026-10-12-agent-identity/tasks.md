## 0. Delivery start

- [x] 0.1 Run `agent-process start_change agent-identity --planner Claude --implementer Claude` for tracking issue 357. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/agent-identity`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Write the tests of the scenario map below against a signature stub of `skills/agent-process/scripts/agent_identity.py` (`main(argv)` with two fake `gh` runners, the person's and the bot's, as in `tests/publisher/test_activate_protection.py`; D4). In `tests/publisher/test_agent_identity.py`, also write:
  - `test_dry_run_issues_only_reads`: every `gh` and `git config` call of a dry-run on a fresh repository is a read
  - `test_replan_names_the_differing_transition`: a ruleset that still plans after the write exits 1 naming the ruleset

  In `tests/publisher/test_skill_check.py`, `test_identity_missing` is parametrized: no `GH_TOKEN`, a `GH_TOKEN` the settings do not hold, and settings that cannot be read.

  In `tests/publisher/test_reusable_workflows.py`, rename `test_release_workflow_enables_auto_merge` to `test_release_workflow_approves_and_enables_auto_merge` (D5) and extend it: under the same `prs_created` condition, a step before the auto-merge step runs `gh pr review --approve` on the parsed PR number with `GH_TOKEN: ${{ github.token }}`, and the auto-merge step keeps `RELEASE_PLEASE_TOKEN`. Run `agent-process check_red` on these node ids and commit RED with the Group 1 ticks

## 2. Agent identity (design D1–D4)

- [x] 2.1 Make `plan` of `skills/agent-process/scripts/activate_protection.py` read the ruleset name from `want["name"]` instead of `NAME` (D4). Verify that `python -m pytest tests/publisher/test_activate_protection.py` passes unchanged
- [x] 2.2 Add `skills/agent-process/templates/approval_ruleset.json` (D2: on `~DEFAULT_BRANCH`, no bypass actor, one `pull_request` rule with `required_approving_review_count` 1, `dismiss_stale_reviews_on_push` true, `require_last_push_approval` and the other owned parameters false) and implement `agent_identity.py` as specified in "Agent identity converges", with the helpers that D4 names. After a confirmed run, it prints that `GH_TOKEN` applies after a Claude Code restart. Add the script to the `MOVED_SCRIPTS` sets of `tests/publisher/test_plugin.py` and `tests/publisher/test_start_change.py`. Verify with `python -m pytest tests/publisher/test_agent_identity.py tests/publisher/test_plugin.py`. Commit

## 3. Session marker (design D6)

- [x] 3.1 Add the identity check to `skills/agent-process/templates/skill_check.py` next to `_pre_push`: it reads `GH_TOKEN` from its environment, and `_texts` gains the identity fix (D6). Verify with `python -m pytest tests/publisher/test_skill_check.py`. Commit

## 4. Release approval (design D5)

- [x] 4.1 In `.github/workflows/release-please.yml`, add the step "Approve the release PR" of D5 before "Enable auto-merge on the release PR", parsing the PR number in `run` as that step does, and update the header comment. Verify with `python -m pytest tests/publisher/test_reusable_workflows.py`. Commit

## 5. Guard removal (design D6)

- [x] 5.1 Delete `skills/agent-process/scripts/git_guard.py` and `tests/publisher/test_git_guard.py`. Remove the `PreToolUse` `Bash` entry from `hooks/hooks.json`, the guard hook tests from `tests/publisher/test_plugin.py` (`GUARDED_PAYLOAD` and its tests), `git_guard.py` from both `MOVED_SCRIPTS` sets, and the guard sentence of the docstring of `tests/agent_process/test_delivery_gate_wiring.py`. Verify that `git grep -n git_guard -- ':!openspec' ':!tests/publisher/test_close_review.py'` prints nothing and that `python -m pytest tests/publisher tests/agent_process` passes. Commit

## 6. Docs (design D1–D6)

- [x] 6.1 In `skills/agent-process/SKILL.md` Install, replace the guard paragraph with the identity step: the bot account and `gh auth login -s project,workflow` as the bot, then `agent_identity --dry-run` and `--confirm`, then the restart
- [x] 6.2 Add `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` from the template (D1–D3, D6). It records the person's approval as the gate (D2: the rejected `update` bypass, why `require_last_push_approval` stays off, update first and approve last), the Actions approval of the release PR (D5) and the worktree limit of D3. Its deletion condition: local Claude Code gets a session-scoped GitHub credential, as cloud sessions do. Amend ADR 0031 D4: the release workflow approves the PR with `GITHUB_TOKEN` before enabling auto-merge, and the repository allows Actions approvals (D5); its Confirmation names the renamed test. Verify that `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py tests/agent_process/test_issue_refs.py` passes. Commit as `docs: the agent runs under its own identity`

## 7. Verify

- [x] 7.1 Run `/simplify` without an argument and commit its edits
- [x] 7.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 7.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 8. Deliver

- [x] 8.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change agent-identity`. Verify that the script archives, commits and pushes the branch
- [ ] 8.2 Run `gh pr create --title "feat: agent-identity" --body-file <report>`. The report references tracking issue #357 plainly, never with `Closes`. It carries the scenario → test map and the steps of design, Migration Plan
- [ ] 8.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 8.4 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change. The explanation gives the person, before the merge, `gh api -X PUT repos/<repo>/actions/permissions/workflow -F can_approve_pull_request_reviews=true -f default_workflow_permissions=read` (D5; `read` is the value it has today), and the post-merge steps:
  - create the bot account, run `gh auth login -s project,workflow` as the bot, then `gh auth switch --user <person>`
  - run `agent-process agent_identity --bot <login> --dry-run`, then `--confirm`, and restart Claude Code
  - verify that the next session start shows no `agent-process agent identity not set`, and that in that session, after `EnterWorktree`, `gh api user -q .login` prints the bot
  - on the agent's next PR with green checks and no approval, `gh pr view <N> --json reviewDecision,mergeStateStatus` reads `REVIEW_REQUIRED` and `BLOCKED`. Before approving it, the person runs `GH_TOKEN=$(gh auth token --user <bot>) gh api -X PUT repos/<repo>/pulls/<N>/merge -f merge_method=squash` from their own terminal and sees HTTP 405 with a repository rule violation naming the required approving review; it is a PR the person means to merge anyway, so a wrong rule costs nothing
  - the next release PR carries the `github-actions` approval and merges without the person (`gh release view v<version>`)
  - delete `ekolvah/agent-process-sandbox-restrict-updates`

  The person approves and merges it

## Scenario → test map

| Scenario | Test |
|---|---|
| `distribution` / Confirmed run on a fresh repository | `tests/publisher/test_agent_identity.py::test_confirmed_run_on_a_fresh_repository` |
| `distribution` / A precondition fails | `tests/publisher/test_agent_identity.py::test_a_precondition_fails` (parametrized: settings not ignored, no token, other login, admin) |
| `distribution` / Rerun | `tests/publisher/test_agent_identity.py::test_rerun` |
| `distribution` / Identity missing | `tests/publisher/test_skill_check.py::test_identity_missing` |
| `distribution` / Identity set | `tests/publisher/test_skill_check.py::test_identity_set` |
| `distribution` / Version places agree | unchanged; `tests/publisher/test_plugin.py::test_version_drift` |
| `distribution` / Release PR opened or updated | `tests/publisher/test_reusable_workflows.py::test_release_workflow_approves_and_enables_auto_merge`; live on the first release PR after the ruleset is applied (task 8.4) |
| `distribution` / No release PR change | `tests/publisher/test_reusable_workflows.py::test_release_workflow_parses_no_unset_output`, `::test_release_workflow_approves_and_enables_auto_merge` (the approval step's `prs_created` guard) |
| `distribution` / Release PR merged | n/a: platform behaviour of release-please-action; observed with `gh release view v<version>` after the first release under the ruleset (task 8.4) |
| `review-and-merge` / Merge from Claude Code | `tests/publisher/test_agent_identity.py::test_approval_ruleset_body` asserts the required approval and no bypass (the sandbox observed that rule blocking a PR until an approval, proposal, Why); live after `--confirm`: `REVIEW_REQUIRED` and `BLOCKED` on the agent's green PR, and the bot's REST `PUT .../merge` refused with 405 (task 8.4) |
