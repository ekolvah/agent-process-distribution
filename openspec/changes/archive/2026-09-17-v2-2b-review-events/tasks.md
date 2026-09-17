## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/v2-2b-review-events/architect-review.md` exits 0. The tracking issue is the one of the open PR this change is delivered on (#130, PR #137); it was closed by the merge of the first PR (#136) and is not in `Planned` — this change is the delta of that PR's review fixes (owner's decision on Codex's P1 of `26bc2da`), so the propose-run gate on `Planned` does not apply: no issue is created, nothing is asked
- [x] 0.2 Branch: `git branch --show-current` prints `issue-130-review-events` — the branch of the PR (#137); no `gh issue develop`
- [x] 0.3 No status move: the tracking issue is closed (#130)
- [x] 0.4 Provenance: the PR body names planner and implementer (Claude, both; #137)

## 1. RED first

- [x] 1.1 `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (scenario "Review fix changes a spec"): assert `never a direct edit of \`openspec/specs/\`` in the Deliver entry between the reply clause and `three rounds`; `python .agent-process/scripts/check_red.py tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` reports RED

## 2. The rule and the delta

- [x] 2.1 `openspec/config.yaml`, `rules.tasks`, Deliver group: after the `P2`/`P3` clause, `a fix that changes a spec goes through a change of its own on the PR branch — npx -y @fission-ai/openspec@1.13.0 new change <name>, the delta under its specs/, validate --strict, python .agent-process/scripts/archive_change.py <name> — never a direct edit of openspec/specs/: the archive is what carries a spec`; `agent-process.md` step 4 names the same rule in one sentence; `python -m pytest tests/publisher/test_planning_workflow.py -q` green
- [x] 2.2 `git checkout main -- openspec/specs/implementation/spec.md openspec/specs/review-and-merge/spec.md`; write this change's deltas for `review-and-merge` (both modified requirements, full text) and `implementation` ("Delivery steps are tasks of every change", full text, with the scenario "Review fix changes a spec")
- [x] 2.3 ADR 0027: the reply-driven re-run observed on the PR (#137: resolve 18:04:21Z → reply 18:04:22Z → run 35256579419, enforcement listed the two open threads only) and this decision

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` reports only the pre-existing failure of the untracked `v2-2-delivery` (a change of #112, not of this PR) and `python .agent-process/scripts/ci_check.py` green with that directory set aside; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [x] 4.1 `git status --short` empty for this change's files → `python .agent-process/scripts/archive_change.py v2-2b-review-events` (marks its own task, archives — applying the deltas to `openspec/specs/` —, commits, pushes)
- [ ] 4.2 The PR exists (#137): `python .agent-process/scripts/update_pr_body.py 137 --body-file <report>` — the report names this change and the scenario → test map below
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request 137` → `python .agent-process/scripts/wait_for_pr.py 137` → resolve the two `P1` threads of `26bc2da` this push addresses with `python .agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr 137 --thread <id>`, reply after each resolve. The three fixer rounds of the PR are spent (#137): anything further is left to the person with a reply. The person merges. No tick after the archive; a run interrupted after it continues from `gh pr view 137`

## Scenario → test map

- review-and-merge / Head from a fork, Event other than a push → `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads` (on the branch, `26bc2da`)
- review-and-merge / Review event re-runs the check → `tests/publisher/test_reusable_workflows.py::test_agent_review_caller_follows_review_events` (on the branch, `397c54f`)
- implementation / Tasks of a new change, Blocking thread addressed, Review fix changes a spec → `tests/publisher/test_planning_workflow.py::test_tasks_of_a_new_change` (task 1.1)
- implementation / Propose run stopped before its tail → `tests/publisher/test_planning_workflow.py::test_plan_approved` (existing)
