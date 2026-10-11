## 0. Delivery start

- [x] 0.1 Run `agent-process start_change dashboard-per-task-trends --planner Claude --implementer Claude` for tracking issue 402. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/dashboard-per-task-trends`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [ ] 1.1 no RED: the change edits host state (dashboard `aqxk4q`) and one document. It is checked live in 2.2

## 2. Dashboard (design D1–D3)

- [ ] 2.1 `GET /api/dashboards/uid/aqxk4q` and verify `version` is 8; if not, stop and compare with the design's Context. From that JSON remove panels 1–3 and 5–15 and the variables `task` and `attempt`, remove panel 17's transformations, edit panel 19 and add the two panels of D1 styled like panel 19, lay the six trends out three per row with `w: 8`, and rewrite panel 4 and the description per D3. Save with `POST /api/dashboards/db`, `overwrite: false`
- [ ] 2.2 Verify that the save returns version 9 and that a `GET` of the UID has the row, the table, the text panel and the six trends of D1, no templating variable, and on the edited panel 19 an override for `lines` with `custom.axisPlacement: right` and unit `short`. Verify that `GET /api/dashboards/uid/aqxk4q/versions` still lists version 8, and that every link in panel 4 and the description names a heading of `.agent-process/docs/telemetry-measurement-setup.md` (`grep -n '^## '`). Run the targets of panels 19 and the two new panels, taken from that `GET`, in one `POST /api/ds/query` over `now-180d`; verify that PR 401 gives `hours` 2.07, `lines` 824, `failed` 18, `denied` 0 and `compactions` 4, and that the rows of PRs 390, 392 and 397 give `null` for the telemetry readings

## 3. Document (design D3)

- [ ] 3.1 In `.agent-process/docs/telemetry-measurement-setup.md`, rewrite the *Recorded readings* paragraph of "Per-task readings" per D3. Verify that `git grep -n aqxk4q -- .agent-process/docs/telemetry-measurement-setup.md` prints a line of that section; it prints nothing today. Commit as `docs: per-task trends on the dashboard`

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument and commit its edits
- [ ] 4.2 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 4.3 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `agent-process archive_change dashboard-per-task-trends`. Verify that it archives the change with no spec update, commits and pushes the branch
- [ ] 5.2 Run `gh pr create --title "docs: dashboard-per-task-trends" --body-file <report>`. The report names tracking issue #402 as a plain reference, never `Closes`, and carries the replaced version 8, the 2.2 readings and the scenario → test map
- [ ] 5.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- No delta scenarios (`skip_specs: true`); see 1.1. D1–D3 are checked live in 2.2.
  The document is checked by the `git grep` in 3.1 and by the doc tests in 4.3.
