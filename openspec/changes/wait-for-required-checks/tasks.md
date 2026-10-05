## 0. Delivery start

- [x] 0.1 Run `agent-process start_change wait-for-required-checks --planner Claude --implementer Claude` for tracking issue 348. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/wait-for-required-checks`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_pr_delivery.py`, give the fake `_Sequence` a `required: list[str] | None` (default `["agent-process / quality", "agent-review / agent-review"]`), an `extra_rule: bool` (default off) and a `rules_rc`: it answers `gh pr view … --json baseRefName` with `main` and `gh api repos/{owner}/{repo}/rules/branches/main` with the rules as observed in this repository: a `required_status_checks` rule holding those contexts, a `pull_request` rule, and a second `required_status_checks` rule holding `pr-title` when `extra_rule` is set (`[]` when `required` is empty and no `extra_rule`; exit `rules_rc` with a stderr when non-zero). Rename the check names of `test_pending_review` and `test_empty_rollup_after_push` from `quality` / `agent-review` to `agent-process / quality` / `agent-review / agent-review`, the names `gh pr checks` reports (design D1). Verify that `python -m pytest tests/publisher/test_pr_delivery.py -q` still passes on the unfixed script
- [x] 1.2 Add `test_required_check_not_yet_attached`: a rollup of only `CodeQL` and `Analyze (python)` passed, `timeout=120` → exit 3, both required contexts in the output, no `clean:`; the foreign checks plus `agent-process / quality` passed → the timeout line names `agent-review / agent-review` only; foreign checks first, then foreign and both required passed → exit 0 with `clean:`; `extra_rule=True`, both plugin contexts passed and `pr-title` absent → the timeout line names `pr-title` only (every rule is collected, not the first); `rules_rc=1` → `RuntimeError` carrying the stderr (exit 2 in `main`)
- [x] 1.3 Add `test_no_required_checks_on_the_base_branch`: `required=[]`, a rollup of one passed check → exit 0 with `clean:`, and the output's first line starts `note: main requires no status check`
- [x] 1.4 Run `agent-process check_red tests/publisher/test_pr_delivery.py::test_required_check_not_yet_attached tests/publisher/test_pr_delivery.py::test_no_required_checks_on_the_base_branch`. Verify that it prints `RED: 2 failed` and exits 0, each failing in its body (exit 0 where 3 is expected; no `note:` line). Commit with the Group 1 ticks as `test(implementation): wait_for_pr waits for the required checks`

## 2. Required checks

- [x] 2.1 In `skills/agent-process/scripts/wait_for_pr.py`, before the loop read `baseRefName` and `gh api repos/{owner}/{repo}/rules/branches/<base>` through `_json`, and collect the `context` of every `required_status_checks` rule's `parameters.required_status_checks` (D1); when none, print the `note:` line once (D2). Per read compute the required contexts absent from the head's check names; settle only when the rollup is non-empty, nothing is pending and nothing is absent; otherwise reset the agreement and wait on the pending names, then `<absent> (not reported)`, keeping `no checks reported` for an empty rollup (D3). Update the module docstring's settle sentence. Verify that `python -m pytest tests/publisher/test_pr_delivery.py -q` passes
- [x] 2.2 In `skills/agent-process/SKILL.md` Delivery, change "agree that all checks on one head concluded" to "agree that all checks on one head concluded, every check the base branch requires among them". Verify that `python -m pytest tests/publisher -q` passes
- [x] 2.3 In `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`, replace (the sentence wraps across two lines) "Not proved: a gap longer than 30 s between the runs of one push." with "Not proved: a check the base branch does not require attaching more than 30 s after the required ones concluded (issue 348 closed the gap for required checks; such a check does not gate the merge)." (design D3). In the same ADR's `wait_for_pr` bullet (lines 212–215), replace "every workflow run attaches queued at once; required contexts are not readable without admin rights, so the script trusts a concluded rollup only when two consecutive polls list the same checks" with "the runs of one push can attach minutes apart (issue 348: a foreign CodeQL first, the process's runs two minutes later); the required checks of a ruleset are readable without admin rights, classic protection's are not, so the script waits for every check the base branch's rules require and trusts a concluded rollup only when two consecutive polls list the same checks". Verify with `grep -n "issue 348" .agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md` (two lines)
- [x] 2.4 Run `agent-process wait_for_pr 346 --timeout 60` from the worktree. Verify that it ends `clean:` on the merged PR's head, with no `note:` line (this repository requires three checks). Commit 2.1–2.4 as `fix(implementation): wait_for_pr waits for the required checks`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change wait-for-required-checks`. Verify that it archives the delta into `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: wait-for-required-checks" --body-file <report>`. The report references the tracking issue plainly (#348), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `implementation` / Pending review → `tests/publisher/test_pr_delivery.py::test_pending_review`
- `implementation` / Empty rollup after a push → `tests/publisher/test_pr_delivery.py::test_empty_rollup_after_push`
- `implementation` / Required check not yet attached → `tests/publisher/test_pr_delivery.py::test_required_check_not_yet_attached`
- `implementation` / No required checks on the base branch → `tests/publisher/test_pr_delivery.py::test_no_required_checks_on_the_base_branch`
