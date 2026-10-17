## 0. Delivery start

- [x] 0.1 Run `agent-process start_change nightly-release-merge --planner Claude --implementer Claude` (tracking issue 465), enter the worktree it prints with `EnterWorktree`, and run every later task there; verify the branch is linked to the issue and the plan commit exists

## 1. RED

- [ ] 1.1 In `tests/publisher/test_reusable_workflows.py` add `test_push_to_main`: `release-please.yml` triggers on exactly `push` to `main` and `schedule` with cron `17 0 * * *`, and its release-please action step has `skip-github-pull-request: ${{ github.event_name == 'push' }}` and no `skip-github-release`
- [ ] 1.2 In the same file add `test_release_pr_behind_main`: `release-please-config.json` has `"always-update": true`
- [ ] 1.3 Run `agent-process check_red` with the node ids of 1.1 and 1.2 and commit RED with these ticks

## 2. Nightly release PR

- [ ] 2.1 Apply design decisions 1 and 3 to `.github/workflows/release-please.yml`: the `schedule` trigger, the action input, and a header comment naming ADR 0046 (spec distribution: Push to main)
- [ ] 2.2 Apply design decision 2 to `release-please-config.json` (spec distribution: Release PR behind main)
- [ ] 2.3 Apply design decision 4: add `.agent-process/docs/adr/0046-release-prs-merge-nightly.md` (context, options from design decision 1, outcome, consequences, deletion condition, confirmation naming the tests of group 1 and the first nightly run) and an "Amended by ADR 0046" line in D4 of ADR 0031
- [ ] 2.4 Verify `python -m pytest tests/publisher/test_reusable_workflows.py tests/publisher/test_plugin.py tests/publisher/test_release_pr.py tests/agent_process/test_adr_records.py -q` is green, then commit the group with its ticks

## 3. Verify

- [ ] 3.1 Run `/simplify` without an argument and commit its edits
- [ ] 3.2 Run `openspec validate --strict --all`
- [ ] 3.3 Run the `test` that `.github/agent-process-quality.json` declares

## 4. Deliver

- [ ] 4.1 Run `agent-process archive_change nightly-release-merge`, then `gh pr create --title "feat: nightly-release-merge" --body-file <report>`; the report names tracking issue 465 as a plain reference, carries the scenario-to-test map, names the first nightly run as the live check, and states the principles it interacts with (goal 1, goal 3, §IV, §VII)
- [ ] 4.2 Run `agent-process wait_for_pr <PR>` and handle review threads per the delivery procedure

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Version places agree | `tests/publisher/test_plugin.py::test_version_drift` (unchanged) |
| distribution / Release PR opened or updated | `tests/publisher/test_reusable_workflows.py::test_release_workflow_approves_and_enables_auto_merge` (unchanged); live: the first nightly run after merge |
| distribution / No release PR change | `tests/publisher/test_reusable_workflows.py::test_release_workflow_approves_and_enables_auto_merge` (unchanged: both steps guarded by `prs_created`) |
| distribution / Push to main | `tests/publisher/test_reusable_workflows.py::test_push_to_main` |
| distribution / Release PR behind main | `tests/publisher/test_reusable_workflows.py::test_release_pr_behind_main`; live: the first nightly run that updates an open PR |
| distribution / Release PR merged | n/a: platform behaviour of release-please on merge, unchanged; observed on every release since ADR 0031 |
