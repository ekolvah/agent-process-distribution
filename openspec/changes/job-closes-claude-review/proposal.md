## Why

Issue #349. A clean PR fails `agent-review` at random. Observed on consumer
ekolvah/kinozal_scraper (3.8.3), PR #629, head `3207e04`, run 37339592131: the Claude review
found nothing and posted its closing note as an inline comment (`No findings.` on
`scripts/hooks.py:1`) instead of a PR comment; `Verify the Claude review of the head` read
`review of 3207e04…: absent after 60s` and exited 3. The log shows
`"permission_denials_count": 0` — `gh pr comment` was allowed and not called. A full re-run
posted the PR comment and went green, leaving two unlabelled `No findings.` threads open.

Root cause: the closing comment the job reads as the review is written by the model, so its
existence depends only on the model following the prompt
(`.github/workflows/reusable-agent-review.yml`, prompt of `Claude review`). `head_review.py`
correctly treats inline-only output as an interrupted review; nothing in the job makes a
finished review publish its closing comment.

## What Changes

- `Bash(gh pr comment:*)` leaves the model's allowed tools; the prompt and
  `REVIEW_CONTRACT.md` drop the closing-comment instruction and ask for labelled inline
  findings only.
- A new step `Close the Claude review of the head` fails the check unless the action's
  `conclusion` output is `success` — empty on the action's skip paths, `success` only when the
  session ended normally (observed in `anthropics/claude-code-action@v1`, design D1) — and
  otherwise posts `Reviewed head SHA: <head>` as a PR comment under the workflow token. The
  existing bounded read then verifies it exactly as before.
- The re-run path is unchanged: the pre-review read still returns on the closing comment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review-and-merge`: *Claude reviews every head* — the job, not the action, publishes the
  closing comment once the action concludes `success`; any other conclusion fails the check.

## Impact

- Edited: `.github/workflows/reusable-agent-review.yml`, `.agent-process/REVIEW_CONTRACT.md`,
  `.agent-process/scripts/head_review.py` (docstring: who posts the closing comment),
  `tests/publisher/test_reusable_workflows.py`.
- Spec: `openspec/specs/review-and-merge/spec.md` through the archive of this change.
- Consumers get the fix with the next release through the pinned reusable workflow; no
  consumer file changes.
