## Verdict

approve
Both scripts now read one thing — the D3 token `tracking issue <N>` (design.md D1 step 2, D2 first bullet; tasks.md 2.1 `tracking_issue(tasks_md)`, 2.2 first branch) — and tasks.md 1.1 pins the "token replaced, literal elsewhere → proceeds" cases, the number lands in `tasks.md` before `set_status` with the resume in the failure message, the change's own `tasks.md` keeps the literal in Group 0 only (today's `sed -i` is safe on it), the RED task works before and after `v2-2d-check-red-test`, and the rule edits (Group 0, review tail) touch no sentence of `v2-2d` or `v2-2e`.

## Findings

none

## Scenario coverage

none — every scenario of `specs/implementation/spec.md` and `specs/planning/spec.md` maps to a named test in `tasks.md` 1.1 (`test_verdict_is_rework`, `test_propose_run_stopped_before_its_tail`, `test_tasks_of_a_new_change_start`, `test_plan_approved_creates_the_issue`, `test_existing_tracking_issue`, `test_rework_verdict`, `test_tasks_of_a_new_change`, `test_plan_approved`); the unchanged scenarios of the modified requirements keep their existing tests.
