## 0. Delivery start

- [x] 0.1 Run `agent-process start_change approval-merges --planner Claude --implementer Claude` for tracking issue 409. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/approval-merges`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `tests/publisher/test_enable_auto_merge.py`: the script loaded with `load_script("enable_auto_merge")` from `tests/publisher/delivery_fakes.py`, one test per `review-and-merge` scenario named as in the map below, with a recording `gh` double that raises `RuntimeError` as `run_gh` does (the refused case: `Auto merge is not allowed for this repository`). In `tests/publisher/test_agent_identity.py`, make `World` answer the repository read and PATCH of `allow_auto_merge` (false on a fresh repository), and expect `planned auto-merge` as the sixth transition and the setting true in `test_confirmed_run_on_a_fresh_repository`, six `unchanged` in `test_rerun`, six `planned` in `test_dry_run_issues_only_reads`. Load `enable_auto_merge` inside each test function, as `test_agent_identity.py` does, so a missing module is a test failure. Add `"enable_auto_merge.py"` to `MOVED_SCRIPTS` in `tests/publisher/test_plugin.py`, and `"agent-process enable_auto_merge"` between `"gh pr create"` and `"agent-process wait_for_pr"` in `test_tasks_of_a_new_change` of `tests/publisher/test_planning_workflow.py`. In `tests/publisher/test_pr_delivery.py`, make `_Sequence` answer the head read `--json headRefOid,state` with `state` from a new `states` iterator (default `OPEN`), only when the command requests `state`, and add `test_pr_no_longer_open`, parametrized over `MERGED` and `CLOSED`: exit 4, the state and `not in the PR` printed, no checks or threads read. Run `agent-process check_red tests/publisher/test_enable_auto_merge.py tests/publisher/test_agent_identity.py::test_confirmed_run_on_a_fresh_repository tests/publisher/test_agent_identity.py::test_rerun tests/publisher/test_agent_identity.py::test_dry_run_issues_only_reads tests/publisher/test_plugin.py::test_shared_skill_owns_the_procedure_and_scripts tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change tests/publisher/test_pr_delivery.py::test_pr_no_longer_open` and commit RED with the Group 1 ticks

## 2. Scripts, transition and procedure (design D1–D3, D5)

- [x] 2.1 Add `skills/agent-process/scripts/enable_auto_merge.py`: `enable_auto_merge(pr, *, gh)` implementing design D1 on `from set_status import Gh, _json, run_gh`; the docstring states the gate and the exit codes. Verify with `python -m pytest tests/publisher/test_enable_auto_merge.py tests/publisher/test_plugin.py::test_shared_skill_owns_the_procedure_and_scripts`
- [x] 2.2 In `skills/agent-process/scripts/agent_identity.py`, add the `auto-merge` step of design D3 last in `_plan`, and its line to the transition list of the module docstring. Verify with `python -m pytest tests/publisher/test_agent_identity.py`
- [x] 2.3 In `skills/agent-process/scripts/wait_for_pr.py`, read `headRefOid,state` in `_head` and exit 4 per design D5, with exit 4 in the module docstring's exit codes. Verify with `python -m pytest tests/publisher/test_pr_delivery.py`
- [x] 2.4 In `skills/agent-process/SKILL.md`: Delivery, after the `gh pr create` sentence, run `agent-process enable_auto_merge <PR>`, whose outcome the explanation of the delivered change states; after the `wait_for_pr` sentence, exit 4 (the PR is no longer open) stops the loop and is reported to the person; Tasks step 5, "The person merges." becomes "The person's approval merges."; Install step 6, "so the person approves and merges the agent's PRs" becomes "so the person's approval merges the agent's PRs". Verify with `python -m pytest tests/publisher/test_planning_workflow.py`. Commit

## 3. ADR (design D4)

- [x] 3.1 Add D7 to `.agent-process/docs/adr/0040-the-agent-runs-under-its-own-identity.md` per design D4, and name `tests/publisher/test_enable_auto_merge.py` and `tests/publisher/test_pr_delivery.py::test_pr_no_longer_open` under Confirmation. Verify with `git diff --stat` that only the ADR changed. Commit

## 4. Verify

- [x] 4.1 Run `/simplify` without an argument, and commit its edits or record `no edits` with the skipped findings in this tick — edits: `_head` renamed `_head_state`; ADR D7 states that a push already made after the merge is reported by the next `wait_for_pr` run, Confirmation rewrapped. Skipped: extracting `_report` (needed for ruff C901), the `--json` field parse of `_Sequence` (architect review: `state` only when asked), docstring length, dropping the `allow_auto_merge` transition (design D3), sharing the repo read with `gh repo view` (one read on a rare command), the private `_json` import (existing pattern)
- [x] 4.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 4.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [x] 5.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change approval-merges`. Verify that it merges the deltas into `openspec/specs/review-and-merge/spec.md`, `openspec/specs/distribution/spec.md` and `openspec/specs/implementation/spec.md`, archives, commits and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: approval-merges" --body-file <report>`. The report references tracking issue #409 plainly, never with `Closes`, and carries the scenario → test map
- [ ] 5.3 Run `agent-process enable_auto_merge <PR>` (this branch's own script). Verify exit 0 and `gh pr view <PR> --json autoMergeRequest` showing `mergeMethod` `SQUASH`; on exit 1 record the `reviewDecision` it read in the report (design D1)
- [ ] 5.4 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push; on exit 4 stop and report the PR state to the person. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 5.5 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change, stating the outcome of 5.3. The person's approval merges it

## Scenario → test map

| Scenario | Test |
|---|---|
| Auto-merge after the PR (`review-and-merge`) | `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` |
| Approval merges (`review-and-merge`) | n/a: platform behaviour; task 5.3 observes its precondition (auto-merge enabled with `SQUASH` on this change's own PR), and the merge on the person's approval happens after the run ends, seen by the person |
| PR no longer open (`implementation`) | `tests/publisher/test_pr_delivery.py::test_pr_no_longer_open` |

Revised after delivery (design, Revision after delivery): the script of 2.1 and the transition of 2.2 removed; the map above is the revised one.
