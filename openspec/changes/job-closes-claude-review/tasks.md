## 0. Delivery start

- [x] 0.1 Run `agent-process start_change job-closes-claude-review --planner Claude --implementer Claude` for tracking issue 349. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/job-closes-claude-review`, moves the change there, sets In Progress and posts the provenance line; enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`, expect `Close the Claude review of the head` between `Claude review` and `Verify the Claude review of the head`; assert `claude["id"] == "claude"` and `gh pr comment` not in `claude_args` (the `--json-schema` absence assertion stays); replace the prompt anchors `last, on every review` and `Reviewed head SHA: <sha>` with `no other comment`, and assert `gh pr comment` and `Reviewed head SHA` are not in the prompt (design D1, D3). In `test_agent_review_skips_the_review_on_a_release_pr`, assert the close step's `if` is the absence condition
- [x] 1.2 Add `test_close_step_posts_the_comment_the_reader_reads`: assert the close step's `if` is the absence condition, `env["CONCLUSION"] == "${{ steps.claude.outputs.conclusion }}"` and no `${{` in its `run`; run that `run` with `git_bash()`, preceded by a `gh` shell function that writes its arguments to a log file, with `CONCLUSION=success`, `REPO`, `PR`, `SHA` in the environment; assert exit 0, the logged arguments start `pr comment <pr> --repo <repo>`, and `head_review.reviewed` returns True for a payload whose one comment, by `github-actions[bot]`, has the logged `--body` (D2)
- [x] 1.3 Add `test_close_step_fails_unless_the_review_concluded`, parametrized over `CONCLUSION` `""` (a skipped action) and `failure`: the same run; assert a non-zero exit, `::error::` in its stdout and no `gh` call logged (D1, D2)
- [x] 1.4 Run `agent-process check_red` on the node ids of 1.1–1.3 (both tests of 1.1, the test of 1.2, both cases of 1.3). Verify that it prints `RED: 5 failed` and exits 0, each failing in its body (the step is missing). Commit as `test(review-and-merge): the job closes the Claude review`

## 2. Review job

- [ ] 2.1 In `.github/workflows/reusable-agent-review.yml`: give `Claude review` `id: claude`; drop `Bash(gh pr comment:*)` from `--allowed-tools`; rewrite the prompt — findings inline and labelled, no other comment, the job posts the closing comment when the review ends (D3); add `Close the Claude review of the head` with `env` `GH_TOKEN`, `CONCLUSION`, `REPO`, `PR`, `SHA` and a `run` that fails with `::error::` naming the conclusion unless it is `success`, and otherwise runs `gh pr comment "$PR" --repo "$REPO" --body "Reviewed head SHA: $SHA"` (D1, D2); update the header comments of the read, close and verify steps. Verify that `python -m pytest tests/publisher/test_reusable_workflows.py -q` passes
- [ ] 2.2 In `.agent-process/REVIEW_CONTRACT.md`, rewrite the publication bullet: one labelled inline comment per finding and no other comment; the job posts the closing comment it reads the review by when the review ends (D3). In `.agent-process/scripts/head_review.py`, change the docstring's first sentences to say the job posts the closing comment once the action concluded `success`. Verify that `python -m pytest tests/publisher -q` passes. Commit as `fix(review-and-merge): the job closes the Claude review`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change job-closes-claude-review`. Verify that it archives the delta into `openspec/specs/review-and-merge/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: job-closes-claude-review" --body-file <report>`. The report references the tracking issue plainly (#349), never with `Closes`, and carries the scenario → test map
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. This repository's caller pins the reusable workflow `@main`, so the PR's own heads are reviewed by the old job; the change takes effect on merge. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `review-and-merge` / New head → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`, `tests/publisher/test_reusable_workflows.py::test_close_step_posts_the_comment_the_reader_reads`
- `review-and-merge` / Silent action → `tests/publisher/test_reusable_workflows.py::test_close_step_fails_unless_the_review_concluded`
- `review-and-merge` / Re-run on a reviewed head → `tests/publisher/test_head_review.py::test_rerun_reads_the_closing_comment_not_inline_nodes`, `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Re-run on an interrupted review → `tests/publisher/test_head_review.py::test_rerun_reads_the_closing_comment_not_inline_nodes`
- `review-and-merge` / Reader failure → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Head from a fork → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Event other than a push → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Release PR review → `tests/publisher/test_reusable_workflows.py::test_agent_review_skips_the_review_on_a_release_pr`
