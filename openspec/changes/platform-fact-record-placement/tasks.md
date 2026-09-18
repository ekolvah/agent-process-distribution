## 0. Delivery start

- [x] 0.1 Gate: `grep -q "^approve" openspec/changes/platform-fact-record-placement/architect-review.md` exits 0. The tracking issue is the one of the open PR this change is delivered on (issue 138, PR 141) — the change is the delta of a review fix of that PR (Deliver rule: a fix that changes a spec goes through a change of its own), so the propose-run gate on `Planned` does not apply: no issue is created, nothing is asked
- [x] 0.2 Branch: `git branch --show-current` prints `observe-platform-facts` — the branch of the PR; no `gh issue develop`
- [x] 0.3 No status move: issue 138 is already `In Progress`
- [x] 0.4 Provenance: the PR body names planner and implementer (Claude, both)

## 1. RED first

- [x] 1.1 no RED: the delta changes the spec text alone; the `proposal` rule of `config.yaml`, which `tests/publisher/test_planning_workflow.py::test_design_on_a_platform_behaviour` reads, already carries the place of the record and does not change

## 2. The place of the record

- [x] 2.1 This change's delta: `planning`, "Platform facts are observed before a design rests on them" — the observation made before the proposal, the record under **Why** or in `design.md` beside the decision; `npx -y @fission-ai/openspec@1.13.0 validate --strict platform-fact-record-placement` valid

## 3. Verify

- [x] 3.1 `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and `python .agent-process/scripts/ci_check.py` green; `git status --short` shows nothing of this change uncommitted

## 4. Deliver

- [ ] 4.1 `git status --short` empty → `python .agent-process/scripts/archive_change.py platform-fact-record-placement` (marks its own task, archives — applying the delta to `openspec/specs/` —, commits, pushes)
- [ ] 4.2 The PR exists (PR 141): answer the `P2` thread with the archived change's name — a `P2` is answered, never resolved by the process
- [ ] 4.3 `python .agent-process/scripts/request_codex_review.py --request 141` → `python .agent-process/scripts/wait_for_pr.py 141`. Round one of three. The person merges. No tick after the archive

## Scenario → test map

- planning / Design on a platform behaviour → `tests/publisher/test_planning_workflow.py::test_design_on_a_platform_behaviour` (existing: the rule names the step before the proposal and the place of the record); the planner's compliance on a given change → n/a: judgement of the propose run, read by the architect review
- planning / Asserted platform fact → `tests/publisher/test_planning_workflow.py::test_asserted_platform_fact` (existing); the reviewer's reading of a given change → n/a: the subagent's judgement, exercised on every propose run
