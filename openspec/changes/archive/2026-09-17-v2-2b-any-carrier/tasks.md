## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/v2-2b-any-carrier/architect-review.md` exits 0. The tracking issue is the one of the open PR this change is delivered on (issue 130, its second PR); it was closed by the merge of the first PR and is not in `Planned` — this change is the delta of a review fix of that PR (Deliver rule: a fix that changes a spec goes through a change of its own), so the propose-run gate on `Planned` does not apply: no issue is created, nothing is asked
- [x] 0.2 Branch: `git branch --show-current` prints `issue-130-review-events` — the branch of the PR; no `gh issue develop`
- [x] 0.3 No status move: the tracking issue is closed
- [x] 0.4 Provenance: the PR body names planner and implementer (Claude, both)

## 1. RED first

- [x] 1.1 `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (`re-request, \`wait_for_pr.py <PR>\` again` < `or the fallback's` < `resolve_review_thread.py`); `python .agent-process/scripts/check_red.py --report <report> <node ids>` reports RED; committed as `99d58a7`

## 2. The review of the head by either carrier

- [x] 2.1 `openspec/config.yaml`, Deliver group, and `agent-process.md` step 4: the wait is on the concluded check of the head, Codex's review or the fallback's; `python -m pytest tests/publisher/test_planning_workflow.py -q` green
- [x] 2.2 ADR 0027: the observation on the review-event bullet (Codex's P1 on `8f272f3`)
- [x] 2.3 This change's delta: `implementation` (the loop sentence); `npx -y @fission-ai/openspec@1.13.0 validate --strict v2-2b-any-carrier` valid

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` reports only the pre-existing failure of the untracked `v2-2-delivery` (a change of another issue, not of this PR) and `python .agent-process/scripts/ci_check.py` green with that directory set aside; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [x] 4.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py v2-2b-any-carrier` (marks its own task, archives — applying the delta to `openspec/specs/` —, commits, pushes)
- [ ] 4.2 The PR exists: `python .agent-process/scripts/update_pr_body.py 137 --body-file <report>` — the report names this change and the scenario → test map below
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request 137` → `python .agent-process/scripts/wait_for_pr.py 137` → the `P1` thread this push addresses (`PRRT_kwDOUAa7yM6jgJkC`): `resolve_review_thread.py`, `gh run rerun <run-id>`, reply. This round is the owner's decision (2026-09-17, "пофикси"); anything further is left to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view 137`

## Scenario → test map

- implementation / Tasks of a new change, Blocking thread addressed, Review fix changes a spec → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (task 1.1)
- implementation / Propose run stopped before its tail → `tests/publisher/test_planning_workflow.py::test_plan_approved` (existing)
