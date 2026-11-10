## 0. Delivery start

- [x] 0.1 Run `agent-process start_change init-replaces-project-areas --planner Claude --implementer Claude` (tracking issue 493), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/publisher/init_harness.py` extend `Project` and `_project_read` (and its `area()`): a Project id, an `Area` field id, option ids, and `views` (`id`, `name`, `filter`; a copy carries `Open`, `Bugs`, `Empty` and one view per `TEMPLATE_AREAS` option named after it with its filter, as observed in proposal Why); apply `updateProjectV2Field`, `createProjectV2View` (filter `null`), `updateProjectV2View` (`name`, `filter`) and `deleteProjectV2View` to the Project by node id. In `tests/publisher/test_init_remote.py` `_gh_kind` returns `areas` for those four mutations
- [x] 1.2 In `tests/publisher/test_init_remote.py` add: `test_areas_replace_the_template` (`--confirm --area Alpha --area "Beta Two"`, fresh sandbox) — exit 0, the copy's options exactly `Alpha`, `Beta Two`, its views `Open`, `Bugs`, `Empty`, `Alpha`, `Beta Two` with the area filters, writes `copy, issue, link, pr` plus only `areas`, no `manual project-areas` row; `test_areas_retry_completes_views` (linked Project with the template's options, a view `Alpha` with no filter, the template's views) — `planned project-areas`, then one view `Alpha` with its filter and no `Distribution` view; `test_areas_not_replaced`, parametrized over options `Own`, the template linked, and no `Area` field — `unchanged project-areas` and no `areas` write, no `manual project-areas` row for `Own` and the template linked, and for no `Area` field a row without `--area`; `test_invalid_area_exits_2`, parametrized over `""`, `a"b`, and `Alpha` twice — exit 2 and an empty runner log. Parametrize `test_dry_run_writes_nothing_remote` over no flag and `--area Alpha`, the latter asserting the `planned project-areas` line names `Alpha` and each `TEMPLATE_AREAS` option as dropped; in `test_manual_actions_are_printed` assert the areas row contains `--area`
- [x] 1.3 Run `agent-process check_red tests/publisher/test_init_remote.py::test_areas_replace_the_template tests/publisher/test_init_remote.py::test_areas_retry_completes_views tests/publisher/test_init_remote.py::test_areas_not_replaced tests/publisher/test_init_remote.py::test_invalid_area_exits_2 tests/publisher/test_init_remote.py::test_dry_run_writes_nothing_remote tests/publisher/test_init_remote.py::test_manual_actions_are_printed` and commit RED with these ticks

## 2. The areas transition

- [x] 2.1 `skills/agent-process/scripts/init.py`: a repeatable `--area` whose argparse type rejects an empty name or one holding `"`, and `parser.error` on a repeated name. Verify `python -m pytest tests/publisher/test_init_remote.py -q -k invalid_area` passes
- [x] 2.2 `skills/agent-process/scripts/manual.py` (design D2): extend `QUERY`/`AREA`, add `Areas` and `areas(t)` with the three states, and have `rows` print the `project-areas` row for `template` as `... -- re-run init with one --area <name> per area of this repository, or replace the Area options and the area views in the UI{why}` and for `none` with the UI wording only. Verify `python -m pytest tests/publisher/test_init_remote.py -q -k manual` is green
- [x] 2.3 `init.py` (design D2, D4, D5): `_areas_step(ctx, repo, linked, areas)` after `_pre_push_step`, before `readings`, its detail naming the given and the dropped options; the apply per D4. Renumber the docstring's step list with `project-areas` and name its writes among the GitHub writes. Verify `python -m pytest tests/publisher/test_init_remote.py -q` is green, then commit the group with its ticks

## 3. Docs

- [x] 3.1 `skills/agent-process/SKILL.md` Install step 2: the agent picks the consumer's areas from the repository's content and passes one `--area <name>` per area to both runs; `commands/init.md` argument hint gains `[--area <name>]...`. Verify `python -m pytest tests/publisher -q -k "skill or plugin or planning"` is green, then commit with the ticks

## 4. Verify

- [ ] 4.1 Run `/simplify` without an argument and commit its edits
- [ ] 4.2 Run `openspec validate --strict --all`
- [ ] 4.3 Run the `test` that `.github/agent-process-quality.json` declares

## 5. Deliver

- [ ] 5.1 Run `agent-process archive_change init-replaces-project-areas`, then `gh pr create --title "feat: init-replaces-project-areas" --body-file <report>`. The report names tracking issue 493 as a plain reference, carries the scenario-to-test map, and states the principles it interacts with (goal 1, §I, §II, §III, §VI, §VII)
- [ ] 5.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Confirmed run | `tests/publisher/test_init_remote.py::test_remote_writes_are_project_and_pr` (unchanged, no `--area`) |
| distribution / Dry-run | `tests/publisher/test_init_remote.py::test_dry_run_writes_nothing_remote` (gains `--area Alpha`) |
| distribution / Manual actions | `tests/publisher/test_init_remote.py::test_manual_actions_are_printed` (gains `--area` in the row) |
| distribution / Copy gets the consumer's areas | `tests/publisher/test_init_remote.py::test_areas_replace_the_template` |
| distribution / Retry completes the views | `tests/publisher/test_init_remote.py::test_areas_retry_completes_views` |
| distribution / Areas not replaced | `tests/publisher/test_init_remote.py::test_areas_not_replaced` |
| distribution / Invalid area | `tests/publisher/test_init_remote.py::test_invalid_area_exits_2` |
