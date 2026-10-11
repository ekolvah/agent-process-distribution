## 0. Delivery start

- [x] 0.1 Run `agent-process start_change record-task-readings --planner Claude --implementer Claude` for tracking issue 389. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/record-task-readings`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 Write `tests/agent_process/test_task_readings.py` against a signature stub of `.agent-process/scripts/task_readings.py` (`main(argv, environ, github, grafana)` plus the `GitHub` and `Grafana` protocols, design D6). Use in-memory doubles and a `tmp_path` tree with an archived change whose `tasks.md` carries `tracking issue 7` and whose `architect-review.json` carries `round`. The tests are the scenario map below, plus these for the design decisions:
  - `test_absent_field_is_missing_not_zero` (D4): no `tool_result` row with a non-empty `success` leaves `failed` empty with a gap, and no `compaction` row in the repository's lookback leaves `compactions` empty with a gap
  - `test_review_without_round_is_gap` (D4, D5)
  - `test_code_rounds_count_distinct_reviewed_heads` (D4): only the reviewer, duplicate SHAs count once
  - `test_unknown_task_writes_no_row_and_fails` (D5): a `gh` failure before the task is known leaves the CSV unchanged and the exit is non-zero
  - `test_archived_change_matched_exactly` (D3): an archived `YYYY-MM-DD-x-<change>` does not make `<change>` a task

  `test_task_pr_merged` also asserts the exact CSV header of the spec's column list, because the dashboard panels read it. `test_grafana_unreachable` is parametrized over a Grafana HTTP error and an unset credential (D5); the unset case also asserts that no Grafana call is made.

  Run `agent-process check_red tests/agent_process/test_task_readings.py` and commit RED with the Group 1 ticks

## 2. Readings script (design D3–D6)

- [x] 2.1 Implement `.agent-process/scripts/task_readings.py` as in D3–D6: the pure reading returns the row, the adapters are `gh_io.run_gh` and `urllib.request` with `Authorization: Bearer`, and `code_rounds` imports from `head_review` as `release_pr.py` imports `gh_io`. The module docstring and comments carry no issue or PR reference (`no-issue-refs`). Verify with `python -m pytest tests/agent_process/test_task_readings.py`. Commit

## 3. Workflow and state (design D2, D7)

- [x] 3.1 Add `.github/workflows/task-readings.yml` as in D2, the script's env being `GRAFANA_URL: ${{ vars.GRAFANA_URL }}` and `GRAFANA_SERVICE_ACCOUNT_TOKEN: ${{ secrets.GRAFANA_SERVICE_ACCOUNT_TOKEN }}`, and the commit author `github-actions[bot]`. Verify that `python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/workflows/task-readings.yml` passes, that `pull_request` has only `types: [closed]`, and that the file has no `concurrency` key. Commit
- [ ] 3.2 With the person's confirmation, set the one-time state of D7: the variable `GRAFANA_URL` (`gh variable set`), the secret `GRAFANA_SERVICE_ACCOUNT_TOKEN` (`gh secret set`, from the token the person chooses; the agent never prints it), and the orphan branch `task-readings` with only the header line of `task-readings.csv`. Verify with `gh variable list`, `gh secret list`, and `git ls-remote origin task-readings`
- [x] 3.3 Backfill and check the live adapters (D7). Use the same token that 3.2 stored as the secret. In a checkout of `task-readings`, run the script locally for PRs 382, 385 and 388 with `--csv` on that checkout. Verify that 382's row has `task_id=issue-101`, `attempt_id=1`, `lines=998` and `code_rounds=3`, and that its `start`/`cost_usd` are either filled or named in `gap`. Verify that the rows of 385 and 388 name every reading they lack in `gap`, and that all three rows name `plan_rounds` in `gap`, since their archived reviews predate `round`. Run it for release PR 386 and verify that the file is unchanged. With the person's confirmation, commit and push the branch

## 4. Dashboard and docs (design D1, D4)

- [x] 4.1 Add a "Recorded readings" row to `aqxk4q` through the Grafana API, using the version the API returns. It holds an Infinity CSV table of every column, with `gap` highlighted when it is non-empty, and time series of `cost_usd`, `hours`, `code_rounds` and `plan_rounds` over `merged_at`, all from the D1 URL. Update the "Not on this dashboard" text panel. Verify with a GET of the dashboard UID that the new version holds the panels, and that a `/api/ds/query` of the table returns the three backfilled rows
- [x] 4.2 Rewrite the "Per-task readings" section of `.agent-process/docs/telemetry-measurement-setup.md`. It names the workflow, the branch and the CSV URL, the columns with their sources (D4 table), the gap rule, the `--attempt` rule for a re-delivery, and the dashboard row. Drop the hand-read table, whose row is now backfilled, and the commands the script now runs. Keep the "Per-task metrics" queries the script cites. Tasks are named by label values, never by issue or PR number. Verify that `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py tests/agent_process/test_issue_refs.py` passes and that `git grep -E 'glc_|glsa_'` finds nothing. Commit as `docs: recorded task readings`

## 5. Verify

- [x] 5.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 5.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 6. Deliver

- [x] 6.1 With a worktree clean but for `tasks.md`, run `agent-process archive_change record-task-readings`. Verify that it creates `openspec/specs/measurement/spec.md`, archives, commits and pushes the branch
- [ ] 6.2 Run `gh pr create --title "feat: record-task-readings" --body-file <report>`. The report references tracking issue #389 plainly, never with `Closes`. It carries the scenario → test map, the backfilled rows, and the post-merge check: this PR's own row on `task-readings`, or a dispatch with its number (design, Migration)
- [ ] 6.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `agent-process resolve_review_thread`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person with the PR, its head, and each open thread's link and one-line finding
- [ ] 6.4 Once `wait_for_pr` settles a head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change. The explanation gives the person the post-merge check (design, Migration):
  - read the PR's row with `git fetch origin task-readings && git show origin/task-readings:task-readings.csv`
  - if there is no row, run `gh workflow run task-readings.yml -f pr=<PR>`
  - close tracking issue 389 once the row is seen

  The person merges it

## Scenario → test map

| Scenario (`measurement`) | Test |
|---|---|
| Task PR merged | `tests/agent_process/test_task_readings.py::test_task_pr_merged` |
| Re-run for a recorded PR | `tests/agent_process/test_task_readings.py::test_rerun_for_a_recorded_pr` |
| Release PR merged | `tests/agent_process/test_task_readings.py::test_release_pr_merged` |
| Task without telemetry | `tests/agent_process/test_task_readings.py::test_task_without_telemetry` |
| Grafana unreachable | `tests/agent_process/test_task_readings.py::test_grafana_unreachable` |

The spec sentence "A run that cannot write the row SHALL fail" is asserted by
`test_unknown_task_writes_no_row_and_fails`. The column list is asserted by the header check in
`test_task_pr_merged`.

The workflow's trigger, guard and push have no unit test. 3.3 checks them live through the
script, and the post-merge check that 6.4 hands to the person checks the workflow end to end.
