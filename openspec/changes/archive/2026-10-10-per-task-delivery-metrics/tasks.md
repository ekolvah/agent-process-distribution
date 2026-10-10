## 0. Delivery start

- [x] 0.1 Run `agent-process start_change per-task-delivery-metrics --planner Claude --implementer Claude` for tracking issue 383. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/per-task-delivery-metrics`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Add `test_review_round` to `tests/publisher/test_planning_workflow.py`: the schema requires `round`, an integer with minimum 1, and its description states the D5 rule (1 on the first review, one more than the replaced file, a file without `round` counting as 1). Add `test_review_without_round` to `tests/publisher/test_start_change.py`, beside `test_review_not_valid`: a review without `round` exits 2 with an error naming `round`, and nothing is created. The fixtures stay unchanged in RED
- [x] 1.2 Write `tests/agent_process/test_task_metrics.py` against a signature stub of `.agent-process/scripts/task_metrics.py`, with in-memory `Prometheus` and `GitHub` doubles (design D6):
  - `TestStart`: the start query carries `task_id="issue-N"` and `attempt_id="K"` as exact `=` matchers; an empty result gives the start gap and null hours (D1).
  - `TestPullRequest`: one connected PR merged after the start is chosen and a PR merged before it is not; none gives the merge gap; two exit 2 naming both (D2).
  - `TestSize`: `lines_changed` is additions plus deletions (D3).
  - `TestRounds`: code rounds count distinct `Reviewed head SHA:` SHAs by `github-actions` only; plan rounds are the archived review's `round`, and a review without it is a gap (D4, D5).
  - `TestArguments`: a missing `GRAFANA_URL` or `GRAFANA_SERVICE_ACCOUNT_TOKEN` exits 2 naming the variable and no source is read; a bad `--issue` exits 2.
  - `TestExit`: exit 0 without gaps, 1 with any gap, and the printed JSON carries the D6 keys.

  Run `agent-process check_red tests/publisher/test_planning_workflow.py::test_review_round tests/publisher/test_start_change.py::test_review_without_round tests/agent_process/test_task_metrics.py` and commit RED with the Group 1 ticks

## 2. Review round (design D5)

- [x] 2.1 Add the required `round` (integer, `minimum` 1, description stating the D5 rule) to `skills/agent-process/architect-review.schema.json`. Add `"round": 1` to `_valid_review` in `tests/publisher/test_planning_workflow.py` and to `_review` in `tests/publisher/test_start_change.py`. Verify with `python -m pytest tests/publisher/test_planning_workflow.py tests/publisher/test_start_change.py`. Commit

## 3. Readings script (design D1–D4, D6)

- [x] 3.1 Implement `.agent-process/scripts/task_metrics.py`. It has a pure `reading(issue, attempt, prometheus, github)` and the two protocols. The real adapters are `urllib` on the datasource proxy and `gh api graphql` (D5's `object(expression:)` reads included) with `encoding="utf-8"`. `main(argv, environ, ...)` checks the credentials first. Verify with `python -m pytest tests/agent_process/test_task_metrics.py`. Commit

- [x] 3.2 At delivery, by the person's decision (design D6): remove `task_metrics.py` and `test_task_metrics.py`, and put the four reads in the setup doc. Verify each read live on PR 382 against 4.1

## 4. Baseline and docs (design D7)

- [x] 4.1 In the change's worktree, run `python .agent-process/scripts/task_metrics.py --issue 101 --attempt 1`. This is the only check of the real adapters. Verify the live output against the design's observations: PR 382, start `2026-10-10T15:02:36Z`, `lines_changed` 998, `code_rounds` 3, and `plan_rounds` reported as a gap (the review predates `round`). If the start is a gap because the sample expired, record the gap rather than a value
- [x] 4.2 Add the "Per-task readings" section to `.agent-process/docs/telemetry-measurement-setup.md` and extend its question line. The section holds the command, the sources of D1–D5, the ~14-day retention, and the table whose first row is the 4.1 reading with the D7 caveat. Tasks are named by label values (`task_id=issue-101`, `attempt_id=1`), never by issue or PR number, so the `no-issue-refs` hook passes. Verify that `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py` passes and that `git grep -E 'glc_|glsa_'` finds nothing. Commit as `docs: per-task readings baseline`

## 5. Verify

- [x] 5.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 5.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 6. Deliver

- [x] 6.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change per-task-delivery-metrics`. Verify that it applies the planning delta, archives, commits and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: per-task-delivery-metrics" --body-file <report>`. The report references tracking issue #383 plainly, never with `Closes`. It carries the scenario → test map, the baseline reading, and the deferral of the telemetry metrics and window-rejection rules to the sibling issue of #99
- [ ] 6.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change. The person merges it

## Scenario → test map

| Scenario (`planning`) | Test |
|---|---|
| Review finding | `tests/publisher/test_planning_workflow.py::test_review_finding` (unchanged) |
| Review class without evidence | `tests/publisher/test_start_change.py::test_review_not_valid` (unchanged) |
| Over-long rule or bespoke check | `tests/publisher/test_planning_workflow.py::test_over_long_rule_or_bespoke_check` (unchanged) |
| Plan without a prior issue | `tests/publisher/test_start_change.py::test_plan_without_a_prior_issue` (unchanged) |
| Addition without evidence | `tests/publisher/test_start_change.py::test_addition_without_evidence` (unchanged) |
| Rework verdict | `tests/publisher/test_planning_workflow.py::test_rework_verdict`, `tests/publisher/test_start_change.py::test_verdict_is_rework` (unchanged) |
| Plan approved | `tests/publisher/test_planning_workflow.py::test_plan_approved`, `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue` (unchanged) |
| Existing tracking issue | `tests/publisher/test_start_change.py::test_existing_tracking_issue` (unchanged) |
| Review archives with the change | `tests/publisher/test_planning_workflow.py::test_review_archives_with_the_change` (unchanged) |
| Review round | `tests/publisher/test_planning_workflow.py::test_review_round`, `tests/publisher/test_start_change.py::test_review_without_round` |

The reading's decisions D1–D6 have no delta scenario (owner measurement). Its four reads are
documented commands, checked live by 4.1 and 3.2; the script and tests of 1.2 and 3.1 were
removed at delivery (design D6).
