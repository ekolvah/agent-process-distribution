## 0. Delivery start

- [x] 0.1 Run `agent-process start_change projects-v2-api-spike --planner Claude --implementer Claude` (tracking issue 486), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: docs-only (a comment and a remote issue; `skip_specs: true`, no scenario)

## 2. Record and follow-up

- [x] 2.1 `skills/agent-process/scripts/manual.py` `WORKFLOWS` comment (design D1): add that enabling a built-in workflow is UI only — the API reads `name` and `enabled` and can delete a workflow, with no mutation that enables one — citing https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations, and that the row becomes a transition once such a mutation appears. Verify `python -m ruff check skills/agent-process/scripts/manual.py` passes
- [x] 2.2 Create the follow-up issue (design D3) with `gh issue create --title "init replaces the Area options and the area views" --body-file <body>`, the body as design D3 lists it, with issue 486 as its source. Then run `agent-process set_status <new N> --area Distribution`. Verify `gh issue view <new N> --json projectItems` shows it on the Project; commit 2.1 with the ticks as `docs: built-in workflows are UI only`

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [x] 4.1 Run `agent-process archive_change projects-v2-api-spike`, then `gh pr create --title "docs: projects-v2-api-spike" --body-file <report>`, then `gh pr merge <PR> --auto --squash`. The report names tracking issue 486 as a plain reference, gives the per-item answer, links the follow-up issue, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

- No delta scenarios (`skip_specs: true`): n/a, the change records a research answer in a comment and opens an issue; no behaviour changes
