## 1. RED first

- [x] 1.1 `test_plan_approved_creates_the_issue`: without `--area` on the placeholder, stderr lists `Observability`, `Distribution`, `Token efficiency` and no issue is created. `test_plan_approved`: the Architect review section says "choose the area" before `create_tracking_issue.py` and has no "ask". Run `check_red.py` on both; commit as `test(state): the planner chooses the area`

## 2. Implementation

- [x] 2.1 `set_status.area_options(gh)`; `create_tracking_issue` lists them in the `area required` message; `SKILL.md` and `.claude/rules/workflow.md` say "choose". Commit as `feat(state): the planner chooses the area, asking nothing`

## 3. Deliver

- [ ] 3.1 `validate --strict --all`, `ci_check.py`, `archive_change.py planner-chooses-area`, then `@codex review` and `wait_for_pr.py 220`

## Scenario → test map

- `state` / Area chosen by the planner → `tests/publisher/test_planning_workflow.py::test_plan_approved`; `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue`
- `planning` / Plan approved → `tests/publisher/test_planning_workflow.py::test_plan_approved`
- `implementation` / Tasks of a new change → unchanged; its existing test
