## 0. Delivery start

- [x] 0.1 Run `agent-process start_change per-task-telemetry-readings --planner Claude --implementer Claude` for tracking issue 384. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/per-task-telemetry-readings`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 no RED: docs-only and `skip_specs`. Nothing in the tree has behaviour that a test could check

## 2. Live readings (design D1–D3)

- [x] 2.1 Find the `issue-101` gate span. Run the D1 counts query with `[1h]` in place of `[$__range]`, as a range query with a 1-hour step over 2026-10-10 UTC. The span is the hours that have `issue-101` rows. In the same result, verify rule 1 (D2): an hour that holds the plain session of the ADR 0037 gate has a row that is not `issue-`, and any hour with only launched sessions has none (if there is no such hour, record that). Then run the D1 counts and cost queries as instant queries over the span. Verify that the cost equals 1.1960044 (proposal, Source), and read the failed, denied and compaction counts for `issue-101`. Record the readings for the document, without session ids
- [x] 2.2 Run the D3 query with `task_id="issue-101",attempt_id="1"` over the gate span, and compare it per type with the Langfuse usage of the generations tagged `task:issue-101` and `attempt:1`. Verify that they are equal, or record the difference

## 3. Document (design D1–D4)

- [x] 3.1 Edit `.agent-process/docs/telemetry-measurement-setup.md`:
  - Add a "Per-task metrics" section that holds D1, D2 and D4 together with the proposal's observations. It refers to the existing counter-reset paragraph rather than restating it. It carries no issue numbers, session ids, keys or account data, and names the repository only as a placeholder.
  - Rewrite the unlaunched-series sentence of "Which labels carry the task" so it points to rule 1.
  - Extend "Per-session totals" with the task selector (D3).

  Verify that `python -m pytest tests/agent_process/test_doc_headers.py tests/agent_process/test_doc_links.py` passes. Commit as `docs: per-task telemetry readings`

## 4. Verify

- [x] 4.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [x] 4.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [x] 5.1 With a clean worktree, run `agent-process archive_change per-task-telemetry-readings`. Verify that it archives the change with no spec update, commits and pushes the branch
- [ ] 5.2 Run `gh pr create --title "docs: per-task-telemetry-readings" --body-file <report>`. The report references the tracking issue plainly (#384), never with `Closes`. It carries the 2.1 and 2.2 readings, the scenario → test map, and the deferral: the baseline of five launched tasks goes to a later docs PR that closes the issue
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person. Report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`). D1–D3 are covered by the Group 2 live readings,
  and D4 is the procedure for the baseline PR. All are `n/a` in CI, because no test
  contacts Grafana or Langfuse. The document is covered by the doc header and link tests
  in 4.2.
