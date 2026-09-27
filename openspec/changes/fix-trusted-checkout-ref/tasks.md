## 0. Delivery start

- [x] 0.1 Run `python skills/agent-process/scripts/start_change.py fix-trusted-checkout-ref --planner Claude --implementer Claude` for tracking issue 226. Verify that it reads the approved review, creates the linked branch from `origin/main`, sets In Progress, and posts the provenance line before any other work

## 1. RED first

- [x] 1.1 In `tests/publisher/test_reusable_workflows.py`, set `TRUSTED_CHECKOUT["ref"]` to `"${{ job.workflow_sha }}"` and add `test_trusted_checkout_is_the_called_commit`. For `reusable-agent-review.yml` and `quality.yml`, every step whose `with.path` is `trusted` must have `ref: ${{ job.workflow_sha }}` and follow directly after a step named `Require the called workflow commit`. That step's `env.SHA` must be `${{ job.workflow_sha }}`. Its `run`, executed with `bash -c` and `SHA=""`, must exit non-zero with `job.workflow_sha is empty` on stdout. With `SHA` set to 40 hex digits it must exit 0. Run `python skills/agent-process/scripts/check_red.py` with the new test and `test_quality_skips_the_link_on_a_release_pr`, `test_agent_review_skips_the_review_on_a_release_pr` (each finds the checkout by `TRUSTED_CHECKOUT`), and verify that each fails in the test body. Commit as `test(review): trusted checkout is the called commit`

## 2. Workflows (D1, D2)

- [x] 2.1 In `.github/workflows/reusable-agent-review.yml` and `.github/workflows/quality.yml`, set the trusted checkout to `ref: ${{ job.workflow_sha }}` and insert the guard step of D2 right before it. Verify that `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes
- [x] 2.2 In ADR 0031 D2, replace `github.job_workflow_sha` with `job.workflow_sha` and add "(issue 226: the former name was never set)". Verify that `git grep -n "github.job_workflow_sha" -- .github .agent-process tests` prints nothing. Commit Group 2 as `fix(review): trusted checkout is the called commit`

## 3. Verify

- [x] 3.1 Run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and verify that every change and spec passes
- [x] 3.2 Run `python .agent-process/scripts/ci_check.py` and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `python skills/agent-process/scripts/archive_change.py fix-trusted-checkout-ref`. Verify that it archives the delta into `openspec/specs/`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: fix-trusted-checkout-ref" --body-file <report>`. The report names tracking issue 226 as a plain reference (never `Closes`), carries the scenario → test map, and states that the `@main` review callee is observed only after the merge (design, Risks)
- [ ] 4.3 In the log of the PR's `agent-process / link` job, verify that `Require the called workflow commit` passed and that the `with:` block of `Checkout trusted process source` lists a non-empty `ref:`. If it is empty, stop and report it to the person
- [ ] 4.4 Run `python skills/agent-process/scripts/wait_for_pr.py <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread with `python skills/agent-process/scripts/resolve_review_thread.py --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.5 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation in the final message. Tell the person that after the merge, a re-run of `agent-review` on PR 225 must show `Checkout trusted review source` at `main`'s SHA. The person merges

## Scenario → test map

- `review-and-merge` / PR changes a process script → `tests/publisher/test_reusable_workflows.py::test_trusted_checkout_is_the_called_commit` (`ref` is `job.workflow_sha`). The live proof is task 4.3 for `quality.yml` and, after the merge, the PR 225 re-run for the review callee
- `review-and-merge` / Called commit unavailable → `tests/publisher/test_reusable_workflows.py::test_trusted_checkout_is_the_called_commit` (the guard run with an empty `SHA`)
