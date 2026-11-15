## 0. Delivery start

- [x] 0.1 Run `agent-process start_change manual-release-dispatch --planner Claude --implementer Claude` (tracking issue 518), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 In `tests/publisher/test_reusable_workflows.py` extend `test_push_to_main`'s expected trigger with `"workflow_dispatch": None` and its docstring's "only the nightly run" to "only the nightly or a dispatched run"
- [ ] 1.2 Run `agent-process check_red` on `test_push_to_main`, verify it fails because the trigger has no `workflow_dispatch`, and commit RED with the group 1 ticks

## 2. Implementation

- [ ] 2.1 Add `workflow_dispatch:` to `on:` of `.github/workflows/release-please.yml` and change its header comment "Only the nightly run opens or updates the release PR" to "Only the nightly or a manually dispatched run opens or updates the release PR"; verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` is green
- [ ] 2.2 In `.agent-process/docs/adr/0047-release-prs-merge-nightly.md` add `workflow_dispatch` to the triggers its Decision Outcome bullet lists, and add under Consequences: "Neutral, because the person may dispatch the workflow by hand for a daytime release; that run opens, approves and auto-merges the release PR as the nightly run does." Commit 2.1–2.2 with their ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change manual-release-dispatch`, then `gh pr create --title "feat: manual-release-dispatch" --body-file <report>`. The report names the tracking issue as a plain reference, carries the scenario-to-test map, states design **Risks** and names the principles it interacts with (goal 3, §VII)
- [ ] 4.2 Run `gh pr merge <PR> --auto --squash`, then `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Version places agree | `tests/publisher/test_plugin.py::test_version_drift` (unchanged) |
| distribution / Release PR opened or updated | `tests/publisher/test_reusable_workflows.py::test_push_to_main` (the trigger includes `workflow_dispatch`, which `skip-github-pull-request` does not skip) and `::test_release_workflow_approves_and_enables_auto_merge` (unchanged); live: the post-merge `gh workflow run release-please.yml --ref main` |
| distribution / No release PR change | `tests/publisher/test_reusable_workflows.py::test_release_workflow_parses_no_unset_output` (unchanged) |
| distribution / Push to main | `tests/publisher/test_reusable_workflows.py::test_push_to_main` |
| distribution / Release PR behind main | `tests/publisher/test_reusable_workflows.py::test_release_pr_behind_main` (unchanged) |
| distribution / Release PR merged | n/a: live — the tag and Release follow the merge (unchanged) |
