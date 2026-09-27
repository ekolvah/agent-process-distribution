## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py release-auto-merge-unset-pr --planner Claude --implementer <Claude|Codex: the carrier of this apply run>` for tracking issue 213. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 In `tests/publisher/test_reusable_workflows.py`, change `test_release_workflow_enables_auto_merge` so the auto-merge step has `env` `PR_JSON: ${{ steps.release.outputs.pr }}` and no `PR` key, and its `run` contains `jq -er .number` and `gh pr merge --auto --squash "$PR"`; its `if` and `GH_TOKEN` assertions stay. Add `test_release_workflow_parses_no_unset_output` (D2): for every step of `release-please.yml` whose `if` reads `steps.`, no `env` value contains `fromJSON`. Run `python skills/agent-process/scripts/check_red.py tests/publisher/test_reusable_workflows.py::test_release_workflow_enables_auto_merge tests/publisher/test_reusable_workflows.py::test_release_workflow_parses_no_unset_output` and verify both fail in the test body. Commit as `test(release): the auto-merge step parses no unset output`

## 2. Workflow (D1)

- [x] 2.1 Edit the auto-merge step of `.github/workflows/release-please.yml` per D1. The step comment says the output is parsed in `run` because the step `env` is evaluated even when `if` is false (run 36297738914). Verify `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes. Commit as `fix(release): the auto-merge step tolerates an unchanged release PR`

## 3. Verify

- [ ] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py release-auto-merge-unset-pr`. Verify that it archives the delta into `openspec/specs/distribution/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: release-auto-merge-unset-pr" --body-file <report>`. The report names tracking issue 213 as a plain reference, never `Closes`. It carries the scenario → test map and the live check of 4.3
- [ ] 4.3 Run `gh pr comment <PR> --body "@codex review"`, then `python skills/agent-process/scripts/wait_for_pr.py <PR>`. Run both again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 threads without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding. The report tells the person the live check after merge: the `Release Please` run on the merge commit updates #208 and enables auto-merge; #208 merges itself; the run on #208's merge commit is green with the auto-merge step skipped; and `gh release view v2.2.0` names that commit
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR in the final message and link the plain-words explanation of the delivered change. The person merges it

## Scenario → test map

- `distribution` / Version places agree → unchanged; `tests/publisher/test_plugin.py::test_version_drift`
- `distribution` / Release PR opened or updated → `tests/publisher/test_reusable_workflows.py::test_release_workflow_enables_auto_merge`; live on the run that updates #208 after merge (task 4.3)
- `distribution` / No release PR change → `tests/publisher/test_reusable_workflows.py::test_release_workflow_parses_no_unset_output`; live on the run on #208's merge commit (task 4.3)
- `distribution` / Release PR merged → n/a: platform behaviour of auto-merge and release-please-action; observed with `gh release view v2.2.0` after #208 merges (task 4.3)
