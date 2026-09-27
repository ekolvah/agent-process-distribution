## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py replace-priority-with-area --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 219. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 In `tests/publisher/delivery_fakes.py` add an `Area` single-select field (`F_AREA`, options `A_OBS` "Observability", `A_DIST` "Distribution") to `FIELDS`, keeping `Priority`. In `tests/publisher/test_set_status.py`: `test_tracking_issue_created` calls `set_status(7, "In Progress", area="Observability")` and expects edits on `F_STATUS`/`F_AREA`; rename `test_priority_field_drift` → `test_area_field_drift` (`--area Urgent` → exit 2 listing `Observability` and `Distribution`, no edit; and a `FIELDS` without `Area` → exit 2 naming the fields, no edit); rename `test_priority_only` → `test_area_only` (`["7", "--area", "Observability"]` → one edit on `F_AREA`). Verify with the 1.4 run
- [x] 1.2 In `tests/publisher/test_start_change.py` replace every `--priority High` with `--area Observability`; `test_plan_approved_creates_the_issue` expects the resume hint `7 Planned --area Observability` and "area" in the required-argument error; `test_existing_tracking_issue` expects `--area` refused with `area is set at creation` in stderr (today's argparse `unrecognized arguments` must not satisfy it). Add `test_area_field_drift_creates_no_issue` (D2): `--area Urgent` on the placeholder → exit 2, stderr lists `Observability` and `Distribution`, the fake `gh` recorded no `issue create`, `tasks.md` still carries `tracking issue <N>`; and with a `FIELDS` without `Area` → exit 2, stderr names `no field 'Area'`, no `issue create`. Verify with the 1.4 run
- [x] 1.3 In `tests/publisher/test_planning_workflow.py::test_plan_approved` assert "area" precedes `create_tracking_issue.py`, which precedes `--area`, in the Architect review section, and that `priority` is absent from it; keep "area" in Group 0's absent list alongside "priority". In `tests/publisher/test_init_remote.py::test_manual_actions_are_printed` expect exactly one `manual project-areas: ` row naming `Area`. Verify with the 1.4 run
- [x] 1.4 Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_set_status.py::test_tracking_issue_created tests/publisher/test_set_status.py::test_area_field_drift tests/publisher/test_set_status.py::test_area_only tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue tests/publisher/test_start_change.py::test_existing_tracking_issue tests/publisher/test_start_change.py::test_area_field_drift_creates_no_issue tests/publisher/test_planning_workflow.py::test_plan_approved tests/publisher/test_init_remote.py::test_manual_actions_are_printed` and verify every test fails in its body. Commit as `test(state): Area replaces Priority at creation`

## 2. Scripts (D1–D3)

- [x] 2.1 `set_status.py` (D1): `--area` replaces `--priority`; `set_status(..., area=...)` writes `Area` through `_option_id`; add `check_area(area, gh)` (read only, D2) that raises the same `ValueError` as `_option_id` for an unknown option or a missing `Area` field; update the docstring and the `ok:` line. Verify `python -m pytest tests/publisher/test_set_status.py -q` passes
- [x] 2.2 `create_tracking_issue.py` (D2, D3): drop `PRIORITIES` and `choices`; `--area` required on the placeholder and refused on an existing issue; on the create branch check the name with `check_area(area, gh)` before `gh issue create`; resume hint and `ok:` line say `--area`. `start_change.py`: `NOT_FINISHED` says `--area <name>`. Verify `python -m pytest tests/publisher/test_start_change.py -q` passes. Commit as `feat(state): the process sets Area, not Priority, at creation`

## 3. Installer and docs (D4)

- [x] 3.1 `init.py` `_manual`: add the `manual project-areas: {where}/settings -- replace the Area options and the area views with this repository's own` row; the module docstring names three rows. Verify `python -m pytest tests/publisher/test_init_remote.py -q` passes
- [x] 3.2 `skills/agent-process/SKILL.md` Architect review: "ask once for the area … `--area <name>`" (the Project's `Area` options); `.claude/rules/workflow.md`: ask for the area and run `set_status.py <N> --area <name>`; `openspec/config.yaml` context: "in `Planned` with its area". Verify `python -m pytest tests/publisher/test_planning_workflow.py -q` passes and `rg -n -e "--priority" -e "High|Medium|Low" skills .claude openspec/config.yaml` finds nothing. Commit as `docs(state): ask for the area at issue creation`

## 4. Verify

- [x] 4.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 4.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes
- [x] 4.3 Read the template live: `gh api graphql -f query='{user(login:"ekolvah"){projectV2(number:4){public fields(first:30){nodes{... on ProjectV2SingleSelectField{name options{name}}}}}}}'` and verify it is public, `Status` has exactly the four options, `Priority` has `High`, `Medium`, `Low`, and `Area` has at least one option; record the output for the PR report

## 5. Deliver

- [ ] 5.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py replace-priority-with-area`. Verify that it archives the deltas into `openspec/specs/state/spec.md`, `openspec/specs/distribution/spec.md`, `openspec/specs/planning/spec.md` and `openspec/specs/implementation/spec.md`, commits, and pushes the branch
- [ ] 5.2 Run `gh pr create --title "feat: replace-priority-with-area" --body-file <report>`. The report names tracking issue 219 as a plain reference, never `Closes`, and carries the scenario → test map and the 4.3 output
- [ ] 5.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`. Run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 5.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR in the final message and link the plain-words explanation of the delivered change. The person merges it

## Scenario → test map

- `state` / Tracking issue created → `tests/publisher/test_set_status.py::test_tracking_issue_created`
- `state` / Area asked once → `tests/publisher/test_planning_workflow.py::test_plan_approved`; `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue`; `tests/publisher/test_start_change.py::test_existing_tracking_issue`
- `state` / Area field drift → `tests/publisher/test_set_status.py::test_area_field_drift`; `tests/publisher/test_start_change.py::test_area_field_drift_creates_no_issue`
- `state` / Area only → `tests/publisher/test_set_status.py::test_area_only`
- `state` / Several linked Projects → unchanged; `tests/publisher/test_set_status.py::test_several_linked_projects`
- `state` / Template read → n/a: a live read of Project 4, no fake can prove it; task 4.3
- `distribution` / Manual actions → `tests/publisher/test_init_remote.py::test_manual_actions_are_printed`
- `planning` / New task → unchanged; n/a: the edit is the word "area" in the requirement text, asserted by `state` / Tracking issue created
- `planning` / Review finding, Review class without evidence, Over-long rule or bespoke check, Addition without evidence, Rework verdict, Review archives with the change → unchanged; their existing tests
- `planning` / Plan approved → `tests/publisher/test_start_change.py::test_plan_approved_creates_the_issue`; `tests/publisher/test_planning_workflow.py::test_plan_approved`
- `planning` / Existing tracking issue → `tests/publisher/test_start_change.py::test_existing_tracking_issue`
- `implementation` / Tasks of a new change, Propose run stopped before its tail, Verdict is rework, Blocking thread addressed, Review fix changes a spec, Design decision changed at review → unchanged; their existing tests (the requirement text changes only "priority" → "area"; the `propose run not finished` hint is asserted by `tests/publisher/test_planning_workflow.py::test_plan_approved` through Group 0)
