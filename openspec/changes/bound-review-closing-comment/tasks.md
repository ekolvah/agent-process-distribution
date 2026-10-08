## 0. Delivery start

- [x] 0.1 Run `agent-process start_change bound-review-closing-comment --planner Claude --implementer Claude` for tracking issue 370. Verify that it reads the approved review, creates the linked branch from `origin/main` in `.claude/worktrees/bound-review-closing-comment`, moves the change there, sets In Progress and posts the provenance line. Enter that worktree with `EnterWorktree` and run every later task there

## 1. RED first

- [x] 1.1 In `tests/publisher/test_close_review.py`, parse bodies with `markdown_it.MarkdownIt("commonmark").parse` and add:
  - `test_message_cannot_hide_the_denials`, parametrized over final messages whose last line is `<!--`, `<details>` or an unclosed ```` ``` ```` (each opens a block that runs to the end of the document), with one `Bash` denial whose command is ``"echo '```'\n<!--"``. Assert that the first `fence` token's content is exactly the denial line. Assert that the fence and the paragraph `Permission denials: 1` come before every `html_block` and `html_inline` token (D1).
  - `test_oversized_denial_is_cut`: one `Write` denial whose `tool_input.content` is 100,000 characters. Assert that `len(body) <= 65_536`, that `Permission denials: 1` is whole, and that the denial line is at most 1,000 characters plus ` … truncated` and ends with it (D2).
  - `test_oversized_body_is_cut`, parametrized over a 100,000-character ASCII message, a message of 100,000 `😀`, and 100 `Bash` denials of 5,000 characters each. Assert that `len(body) <= 65_536` and `len(body.encode("utf-8")) <= 262_144`. Assert that line 1 is the marker, that `Permission denials: <n>` is whole, that the body ends with `… truncated` on a line of its own, and that stdout carries `::warning::` (D3).
  - Rewrite `test_multiline_denial_stays_on_one_line`: the heredoc denial is the one line of the `fence` token's content (D1).
- [x] 1.2 Run `agent-process check_red tests/publisher/test_close_review.py::test_message_cannot_hide_the_denials tests/publisher/test_close_review.py::test_oversized_denial_is_cut tests/publisher/test_close_review.py::test_oversized_body_is_cut tests/publisher/test_close_review.py::test_multiline_denial_stays_on_one_line`. Verify that it prints `RED: 8 failed` and exits 0. Commit as `test(review): the closing comment is unbounded and the message can hide the denials`

## 2. Bounded closing comment

- [x] 2.1 In `.agent-process/scripts/close_review.py`:
  - Cut a denial line at 1,000 characters with ` … truncated` (D2).
  - Build the body as marker, blank line, `Permission denials: <n>`, then the denial lines inside ```` ``` ```` fences when there are any, then a blank line and the final message (D1).
  - Cut a body over 60,000 characters to 60,000, append `\n\n… truncated\n`, and print `::warning::The closing comment of <sha> is cut at 60000 characters` (D3).
  - Rewrite the module docstring for the new order and the bounds.

  Verify that `python -m pytest tests/publisher/test_close_review.py tests/publisher/test_reusable_workflows.py tests/publisher/test_head_review.py -q` passes. Commit as `fix(review): bound the closing comment and list the denials before the message`

## 3. Verify

- [ ] 3.1 Run `openspec validate --strict --all` and verify that every change and spec passes
- [ ] 3.2 Run the `test` that `.github/agent-process-quality.json` declares and verify that it passes

## 4. Deliver

- [ ] 4.1 With a clean worktree, run `agent-process archive_change bound-review-closing-comment`. Verify that it archives the delta into `openspec/specs/review-and-merge/spec.md`, commits, and pushes the branch
- [ ] 4.2 Run `gh pr create --title "fix: bound-review-closing-comment" --body-file <report>`. The report references tracking issue #370 plainly, never with `Closes`. It carries the scenario → test map and the residuals of design Risks (the raw `tool_name`, the lost tail of a cut message). It notes that the new close step first runs on the first PR reviewed after the merge, because the caller pins `@main`
- [ ] 4.3 Run `agent-process wait_for_pr <PR>`, and run it again after each corrective push. Resolve only an addressed older-head P0/P1 thread, with `agent-process resolve_review_thread --repo ekolvah/agent-process-distribution --pr <PR> --thread <id> --reply-file <path>`. Answer P2/P3 without resolving them. If a P0/P1 thread is still open after the third reviewed head, stop pushing and escalate to the person: report the PR, its head, and each unresolved thread's link and one-line finding
- [ ] 4.4 Once `wait_for_pr` settles a green head with no open P0/P1 thread, or at the escalation, report the PR and link the plain-words explanation of the delivered change in the final message. The person merges it

## Scenario → test map

- `review-and-merge` / New head → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`, `tests/publisher/test_reusable_workflows.py::test_close_step_posts_the_comment_the_reader_reads`, `tests/publisher/test_close_review.py::test_body_carries_marker_message_and_denials`
- `review-and-merge` / Silent action → `tests/publisher/test_reusable_workflows.py::test_close_step_fails_unless_the_review_concluded`
- `review-and-merge` / Silent finish → `tests/publisher/test_reusable_workflows.py::test_close_step_fails_on_a_silent_finish`, `tests/publisher/test_close_review.py::test_silent_finish_writes_no_body`
- `review-and-merge` / Denied tool → `tests/publisher/test_close_review.py::test_message_cannot_hide_the_denials`, `tests/publisher/test_close_review.py::test_body_carries_marker_message_and_denials`, `tests/publisher/test_close_review.py::test_denial_without_command_renders_its_input`, `tests/publisher/test_close_review.py::test_multiline_denial_stays_on_one_line`, `tests/publisher/test_reusable_workflows.py::test_close_step_posts_the_comment_the_reader_reads`
- `review-and-merge` / Oversized session → `tests/publisher/test_close_review.py::test_oversized_denial_is_cut`, `tests/publisher/test_close_review.py::test_oversized_body_is_cut`
- `review-and-merge` / Re-run on a reviewed head → `tests/publisher/test_head_review.py::test_rerun_reads_the_closing_comment_not_inline_nodes`, `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Re-run on an interrupted review → `tests/publisher/test_head_review.py::test_rerun_reads_the_closing_comment_not_inline_nodes`
- `review-and-merge` / Reader failure → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Head from a fork → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Event other than a push → `tests/publisher/test_reusable_workflows.py::test_agent_review_reviews_every_head_and_enforces_threads`
- `review-and-merge` / Release PR review → `tests/publisher/test_reusable_workflows.py::test_agent_review_skips_the_review_on_a_release_pr`
