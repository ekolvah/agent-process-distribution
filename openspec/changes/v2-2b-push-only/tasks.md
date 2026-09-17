## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/v2-2b-push-only/architect-review.md` exits 0. The tracking issue is the one of the open PR this change is delivered on (issue 130, its second PR); it was closed by the merge of the first PR and is not in `Planned` — this change is the delta of a review fix of that PR (Deliver rule: a fix that changes a spec goes through a change of its own), so the propose-run gate on `Planned` does not apply: no issue is created, nothing is asked
- [x] 0.2 Branch: `git branch --show-current` prints `issue-130-review-events` — the branch of the PR; no `gh issue develop`
- [x] 0.3 No status move: the tracking issue is closed
- [x] 0.4 Provenance: the PR body names planner and implementer (Claude, both)

## 1. RED first

- [x] 1.1 `tests/publisher/test_reusable_workflows.py::test_agent_review_caller_runs_on_pushes_alone` (the caller's `on` is `pull_request` alone) and `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (`resolve_review_thread.py` < `gh run rerun <run-id>` < `answered on the thread after the resolve` < `three rounds`; no "the reply re-runs the check"); `python .agent-process/scripts/check_red.py --report <report> <node ids>` reports RED; committed as `da77c17`

## 2. Pushes alone, rerun by hand

- [x] 2.1 `agent-review.yml`: `on.pull_request.types: [opened, synchronize]` alone, the comment naming the reason; `python -m pytest tests/publisher/test_reusable_workflows.py -q` green
- [x] 2.2 `openspec/config.yaml`, Deliver group, and `agent-process.md` step 4: resolve → `gh run rerun <run-id>` (the id from `gh pr checks <PR>`) → reply; `python -m pytest tests/publisher/test_planning_workflow.py -q` green
- [x] 2.3 ADR 0027: the wrong inference of the first review-event bullet marked, the observation (`35262221116`: `BLOCKED` → rerun → `CLEAN`), the withdrawn design and what the PR keeps
- [x] 2.4 This change's deltas: `review-and-merge` (the scenario *Review event re-runs the check* restated on the rerun) and `implementation` (the loop sentence); `npx -y @fission-ai/openspec@1.13.0 validate --strict v2-2b-push-only` valid

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` reports only the pre-existing failure of the untracked `v2-2-delivery` (a change of another issue, not of this PR) and `python .agent-process/scripts/ci_check.py` green with that directory set aside; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [ ] 4.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py v2-2b-push-only` (marks its own task, archives — applying the deltas to `openspec/specs/` —, commits, pushes)
- [ ] 4.2 The PR exists: `python .agent-process/scripts/update_pr_body.py 137 --body-file <report>` — the report names this change, the observation and the scenario → test map below
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request 137` → `python .agent-process/scripts/wait_for_pr.py 137` → a `P0`/`P1` thread this push addresses: `resolve_review_thread.py`, `gh run rerun <run-id>`, reply. The three fixer rounds of the PR are spent; this round is the owner's decision (2026-09-17: pushes alone, rerun by hand); anything further is left to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view 137`

## Scenario → test map

- review-and-merge / Review event re-runs the check → `tests/publisher/test_reusable_workflows.py::test_agent_review_caller_runs_on_pushes_alone` (the trigger set) and `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (the rerun between resolve and reply); the merge state itself is the platform's, observed on the PR (ADR 0027)
- review-and-merge / Unresolved blocking thread, Advisory thread, Blocking thread resolved → `tests/publisher/test_blocking_review_threads.py` (existing)
- implementation / Tasks of a new change, Blocking thread addressed, Review fix changes a spec → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (task 1.1)
- implementation / Propose run stopped before its tail → `tests/publisher/test_planning_workflow.py::test_plan_approved` (existing)
