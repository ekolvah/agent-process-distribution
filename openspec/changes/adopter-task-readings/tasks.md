## 0. Delivery start

- [x] 0.1 Run `agent-process start_change adopter-task-readings --planner Claude --implementer Claude` (tracking issue 415), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [x] 1.1 In `tests/agent_process/test_task_readings.py` add `test_first_task_of_a_repository`: no CSV at `--csv`; expect exit 0 and a file holding the header and the PR's row; add an unset `GRAFANA_URL` case to `test_grafana_unreachable`; in `test_task_pr_merged` assert every Grafana query filters `vcs_repository_name` on `GITHUB_REPOSITORY`
- [x] 1.2 In `tests/publisher/test_reusable_workflows.py` add `test_first_record_creates_the_branch`: run the callee's "Prepare the readings worktree" and "Record and push the row" steps in Git Bash, the script replaced by a stub that writes the header and a row, in a `--depth 1` clone of a temporary bare repository without `task-readings` (expect the origin's `task-readings` to hold one commit whose `ls-tree` is only `task-readings.csv` with the header and the row), then a second run onto that branch (expect two commits and both rows); an `origin` that is a missing path fails the step; reuse `tests.agent_process.git_bash.git_bash`
- [x] 1.3 In `tests/publisher/test_reusable_workflows.py` add `test_callee_reads_the_callers_stack`: only `pr` is required, the first checkout is the default branch, and the record step passes `inputs.grafana_url` and the secret as `GRAFANA_URL` and `GRAFANA_SERVICE_ACCOUNT_TOKEN`; add the `task-readings.yml` → `reusable-task-readings.yml` pair to the schema, permissions, trusted-checkout and callee-trigger tests
- [x] 1.4 In `tests/publisher/test_init.py` add `test_task_readings_caller_render`: managed first line, triggers `pull_request: closed` and `workflow_dispatch` with required number `pr`, the job's merged-or-dispatch `if`, `uses` at `@v<CURRENT>`, `with` `pr: ${{ github.event.pull_request.number || inputs.pr }}` and `grafana_url: ${{ vars.GRAFANA_URL }}`, `secrets` `grafana_service_account_token: ${{ secrets.GRAFANA_SERVICE_ACCOUNT_TOKEN }}`; and this repository's caller equals the render but for the header and `@main`
- [x] 1.5 In `tests/publisher/init_harness.py` add `.github/workflows/task-readings.yml` to `CONSUMER_FILES` and extend FakeGitHub's `secret list` branch to `variable list` (`self.variables`, a `variable-list` fault), then in `tests/publisher/test_init_remote.py` add `["variable", "list"]` to `_gh_kind`'s reads and `test_readings_prerequisites_are_printed` (both modes: one `manual task-readings` row with the variables page and both commands, and every issued `gh` command passes `_gh_kind`), set the variable and secret in `test_observed_manual_rows_are_omitted`, and add a `variable-403` case to `test_unreadable_manual_state_is_printed`; add `task-readings.yml` to `TEMPLATES` in `tests/publisher/test_plugin.py`
- [x] 1.6 Run `agent-process check_red` with the node ids of 1.1–1.5 and commit RED with these ticks

## 2. Recording

- [x] 2.1 `upsert` in `.agent-process/scripts/task_readings.py` treats an absent CSV as empty (spec: First task of a repository); verify `test_first_task_of_a_repository`
- [x] 2.2 Add `.github/workflows/reusable-task-readings.yml` (design D1–D3): `workflow_call` inputs and secret, checkout of the default branch, the workflow-commit guard and `trusted` checkout, Python 3.12, "Prepare the readings worktree", then the record-and-push step running `trusted/.agent-process/scripts/task_readings.py` with the gap-row exit code; verify the 1.2 and 1.3 tests
- [x] 2.3 Replace `.github/workflows/task-readings.yml` with the caller at `@main` (design D5); verify `test_task_readings_caller_render` and the pair tests
- [x] 2.4 Commit the group with its ticks

## 3. Installer

- [x] 3.1 Add `skills/agent-process/templates/task-readings.yml` and the `task-readings` file step in `init.py` after `review`, rendered as `_review_text` is (`_template`, `_managed_text`), with its docstring line (spec: The task-readings caller runs at the release tag, The installed footprint is closed); verify `test_task_readings_caller_render` and `test_installed_footprint_is_closed`
- [x] 3.2 Replace `_secret_set` in `manual.py` with one `_secret_names(t)` read shared by `review-secret` and the new `manual task-readings` row, which also reads `gh variable list`, and name it in `init.py`'s docstring and SKILL.md Install step 4 (design D4; spec: Actions credentials are printed, not set, Manual rows follow observed state); verify the 1.5 tests
- [x] 3.3 Commit the group with its ticks

## 4. Documents

- [x] 4.1 Write `.agent-process/docs/adr/0041-adopters-record-task-readings-in-their-own-stack.md` (proposal, Why) and verify `tests/agent_process/test_adr_records.py`
- [x] 4.2 In `telemetry-measurement-setup.md` "Per-task readings", name the callee, the default branch and the branch the first run creates; add an "Adopters" section: the user-level `env` exporting to the adopter's own stack, `OTEL_RESOURCE_ATTRIBUTES` set by hand, the `manual task-readings` row, Grafana Cloud datasource UIDs (design, Non-Goals), public repositories for the dashboard; verify `tests/agent_process/test_doc_links.py`
- [x] 4.3 In `openspec/specs/measurement/spec.md` change the Purpose from "this repository" to a repository with the process installed (a Purpose is not carried by a delta); verify `openspec validate --strict --all`
- [x] 4.4 Commit the group with its ticks

## 5. Verify

- [ ] 5.1 Run `/simplify` without an argument and commit its edits
- [ ] 5.2 Run `openspec validate --strict --all`
- [ ] 5.3 Run the `test` that `.github/agent-process-quality.json` declares

## 6. Deliver

- [ ] 6.1 Run `agent-process archive_change adopter-task-readings`, then `gh pr create --title "feat: adopter-task-readings" --body-file <report>`; the report names tracking issue 415 as a plain reference, carries the scenario-to-test map, and defers the kinozal confirmation run (design, Confirmation) to after the release
- [ ] 6.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| measurement / Task PR merged | `tests/agent_process/test_task_readings.py::test_task_pr_merged` |
| measurement / First task of a repository | `tests/agent_process/test_task_readings.py::test_first_task_of_a_repository`, `tests/publisher/test_reusable_workflows.py::test_first_record_creates_the_branch` |
| measurement / Re-run for a recorded PR | `tests/agent_process/test_task_readings.py::test_rerun_for_a_recorded_pr` |
| measurement / File with an earlier header | `tests/agent_process/test_task_readings.py::test_file_with_an_earlier_header` |
| measurement / Release PR merged | `tests/agent_process/test_task_readings.py::test_release_pr_merged` |
| measurement / Adopter without its stack credentials | `tests/agent_process/test_task_readings.py::test_grafana_unreachable[unset-credential]` (extended to unset `GRAFANA_URL`), `tests/publisher/test_reusable_workflows.py::test_callee_reads_the_callers_stack` |
| distribution / Fresh repository | `tests/publisher/test_init_remote.py::test_installed_footprint_is_closed` |
| distribution / Installation of another release | `tests/publisher/test_init_config.py::test_rerender_replaces_only_owned_content` |
| distribution / Observed done | `tests/publisher/test_init_remote.py::test_observed_manual_rows_are_omitted` |
| distribution / Unreadable state | `tests/publisher/test_init_remote.py::test_unreadable_manual_state_is_printed` |
| distribution / Task-readings caller render | `tests/publisher/test_init.py::test_task_readings_caller_render` |
| distribution / Review prerequisites | `tests/publisher/test_init_remote.py::test_review_prerequisites_are_printed` |
| distribution / Readings prerequisites | `tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` |
