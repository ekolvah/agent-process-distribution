## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py review-bespoke-standard --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 170. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any RED work.

## 1. RED first

- [x] 1.1 In `tests/publisher/test_delivery_scripts.py`, add `"additions": []` to `_review`, then add `test_addition_without_evidence` (design D2). For each of the following `approve` fixtures, both `start_change.main` and `create_tracking_issue.main` exit 2 with the message from the D2 table and create nothing:
  - `problem: "none"`;
  - `problem: "ADR 0027"`;
  - `standard: "none"`;
  - `standard: "None"`;
  - `standard: "N/A"`;
  - `additions` removed.

  An `approve` with `problem: "#113"` and a `rework` with `problem: "none"` pass validation: the first creates the issue, and the second exits naming `rework`.
- [x] 1.2 In `tests/publisher/test_planning_workflow.py`, add `"additions": []` to `_valid_review`. Extend `test_over_long_rule_or_bespoke_check` to assert that the `bespoke` description contains "names every script, check or non-test file of the proposal's Impact", "closes" and "does not fit" (design D3).
- [x] 1.3 Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_delivery_scripts.py::test_addition_without_evidence tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check`. Verify that it exits 0 with both RED, then commit as `test(planning): RED for the additions list of the architect review`.

## 2. Schema

- [x] 2.1 In `skills/agent-process/architect-review.schema.json`, add `additions` to `required` and to `properties` (D1), add the `approve` constraints to `then` (D2), and replace the `bespoke` description (D3). Verify with `python -m pytest tests/publisher/test_delivery_scripts.py tests/publisher/test_planning_workflow.py -q` (green).
- [x] 2.2 Add one bullet to the Observations of ADR 0027 after the issue 149 entry: the cause from proposal.md, Why, and the `additions` list with no script. Verify with `python -m pytest tests/publisher -q` (green), then commit as `fix(planning): additions list makes the bespoke evidence structured`.

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes.
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes. Verify that `git diff --name-only origin/main` lists only the proposal's Impact paths and the change directory.

## 4. Deliver

- [x] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py review-bespoke-standard`. Verify that it applies the `planning` delta, commits the archive, and pushes the branch.
- [ ] 4.2 Run `gh pr create --title "review-bespoke-standard" --body-file <report>`. The report references the tracking issue without `Closes`, carries the scenario → test map, and names issues 113 and 169 as context.
- [ ] 4.3 Run `python .agent-process/scripts/request_codex_review.py --request <PR>` and `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them.
- [ ] 4.4 Run `python .agent-process/scripts/review_gate.py <PR>` on the settled head. Stop at `ready-for-human` or at the three-round escalation.

## Scenario → test map

- `planning / Review finding` → `tests/publisher/test_planning_workflow.py::test_review_finding`
- `planning / Review class without evidence` → `tests/publisher/test_delivery_scripts.py::test_review_not_valid`
- `planning / Over-long rule or bespoke check` → `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check`
- `planning / Addition without evidence` → `tests/publisher/test_delivery_scripts.py::test_addition_without_evidence`
- `planning / Rework verdict` → `tests/publisher/test_planning_workflow.py::test_rework_verdict`
- `planning / Plan approved` → `tests/publisher/test_planning_workflow.py::test_plan_approved` and `tests/publisher/test_delivery_scripts.py::test_plan_approved_creates_the_issue`
- `planning / Existing tracking issue` → `tests/publisher/test_delivery_scripts.py::test_existing_tracking_issue`
- `planning / Review archives with the change` → `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change`
