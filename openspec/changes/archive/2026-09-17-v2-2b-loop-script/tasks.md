## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/v2-2b-loop-script/architect-review.md` exits 0. The tracking issue is the one of the open PR this change is delivered on (issue 130, its second PR); it was closed by the merge of the first PR and is not in `Planned` — this change is the delta of a review fix of that PR (Deliver rule: a fix that changes a spec goes through a change of its own), so the propose-run gate on `Planned` does not apply: no issue is created, nothing is asked
- [x] 0.2 Branch: `git branch --show-current` prints `issue-130-review-events` — the branch of the PR; no `gh issue develop`
- [x] 0.3 No status move: the tracking issue is closed
- [x] 0.4 Provenance: the PR body names planner and implementer (Claude, both)

## 1. RED first

- [x] 1.1 `tests/publisher/test_resolve_review_thread.py::test_close_round_*` (four: the order, refused while running, refused without a run, refused on an empty reply), `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (`--reply-file` in the rule, no `gh run rerun`), `tests/agent_process/test_review_gate.py::TestVerdict::test_a_red_agent_review_routes_the_fixer_through_the_resolve_script` (wait < resolve, `--reply-file`, no window); `python .agent-process/scripts/check_red.py --report <report> <node ids>` reports RED; committed as `0ec3b6a` with the signature stub

## 2. The step after the wait is one command

- [x] 2.1 `resolve_review_thread.py`: `close_round`, `--reply-file`, the `gh` transports; `python -m pytest tests/publisher/test_resolve_review_thread.py -q` green
- [x] 2.2 `review_gate.py`: the `fix-blocking` action and `_red_reason` name `wait_for_pr.py` and the script, no window clause; `python -m pytest tests/agent_process/test_review_gate.py -q` green
- [x] 2.3 `openspec/config.yaml`, Deliver group, and `agent-process.md` step 4: the call and one parenthesis; `python -m pytest tests/publisher/test_planning_workflow.py -q` green
- [x] 2.4 ADR 0027: the retrospective entry (the copies, the rework count, the decision)
- [x] 2.5 This change's deltas: `implementation` (the loop sentence, scenario *Blocking thread addressed*) and `review-and-merge` (scenario *Review event re-runs the check* names the script); `npx -y @fission-ai/openspec@1.13.0 validate --strict v2-2b-loop-script` valid

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` reports only the pre-existing failure of the untracked `v2-2-delivery` (a change of another issue, not of this PR) and `python .agent-process/scripts/ci_check.py` green with that directory set aside; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [x] 4.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py v2-2b-loop-script` (marks its own task, archives — applying the delta to `openspec/specs/` —, commits, pushes)
- [ ] 4.2 The PR exists: `python .agent-process/scripts/update_pr_body.py 137 --body-file <report>` — the report names this change and the scenario → test map below
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request 137` → `python .agent-process/scripts/wait_for_pr.py 137` → the `P1` thread this push addresses (`PRRT_kwDOUAa7yM6jgZGU`): `resolve_review_thread.py --thread --reply-file` — the script's first run on the PR that carries it. This round is the owner's decision (retrospective, 2026-09-17); anything further is left to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view 137`

## Scenario → test map

- implementation / Blocking thread addressed → `tests/publisher/test_resolve_review_thread.py::test_close_round_resolves_reruns_the_head_run_and_replies_in_that_order`, `::test_close_round_refuses_while_the_head_run_is_still_running`, `::test_close_round_refuses_without_a_head_run`, `::test_close_round_refuses_an_empty_reply`; the rule's call → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change`
- implementation / Tasks of a new change, Review fix changes a spec → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change`
- review-and-merge / Review event re-runs the check → `tests/publisher/test_resolve_review_thread.py::test_close_round_resolves_reruns_the_head_run_and_replies_in_that_order` (the rerun of the head's run) and `tests/publisher/test_reusable_workflows.py::test_agent_review_caller_runs_on_pushes_alone` (the trigger set)
- review-and-merge / Unresolved blocking thread, Advisory thread, Blocking thread resolved → `tests/publisher/test_blocking_review_threads.py` (existing)
- implementation / Propose run stopped before its tail → `tests/publisher/test_planning_workflow.py::test_plan_approved` (existing)
