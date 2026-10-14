## 0. Delivery start

- [x] 0.1 Run `agent-process start_change drop-priority-field --planner Claude --implementer Claude` (tracking issue 421), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 no RED: the only delta scenario is a live read of Project 4, which no offline test can prove (task 2.2 reads it); the fake edit of 2.3 changes no test's outcome

## 2. Board

- [x] 2.1 Delete the field (design D1): `gh project field-delete --id PVTSSF_lAHOApeba84Bhf2xzhgbY60` (the `Priority` field of Project 4, read on 2026-10-14)
- [x] 2.2 Read the template live: `gh api graphql -f query='{user(login:"ekolvah"){projectV2(number:4){public fields(first:30){nodes{... on ProjectV2FieldCommon{name dataType} ... on ProjectV2SingleSelectField{options{name}}}} workflows(first:20){nodes{name enabled}}}}}'` and verify the `Template read` scenario holds; record the output for the PR report
- [x] 2.3 Remove the `Priority` entry from `FIELDS` in `tests/publisher/delivery_fakes.py`; commit the group with its ticks

## 3. Verify

- [x] 3.1 Run `/simplify` without an argument and commit its edits
- [x] 3.2 Run `openspec validate --strict --all`
- [x] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Deliver per the skill's Delivery procedure: `agent-process archive_change drop-priority-field`, then `gh pr create --title "feat: drop-priority-field" --body-file <report>` with tracking issue 421, the scenario-to-test map and the 2.2 output in the report
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| state / Template read | n/a: task 2.2 |
