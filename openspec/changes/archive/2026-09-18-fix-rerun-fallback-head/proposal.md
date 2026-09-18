## Why

The step after the wait of the review loop is `resolve_review_thread.py --thread --reply-file`:
resolve, `gh run rerun <id>` of the head's completed `agent-review` run, reply (issue 130,
ADR 0027). `gh run rerun` re-executes the whole run, and the first step of the callee,
*Wait for the Codex review of the head* (`reusable-agent-review.yml`), reads presence for one
login, the Codex app. Observed on `38debbd` of PR 137 (attempts 2 and 3 of run
`35267976560`, started by the script and by the owner): on a head Codex reviewed, the wait of
the second attempt returned on the existing review and the attempt was enforcement alone.
Deduced from the same step, not observed yet: on a head whose first attempt fell back to
Claude, the second attempt waits the Codex timeout again, runs the Claude action again on the
unchanged head — a paid review with a new chance of a finding on a head the fixer did not
change — and only then enforces the resolve (Codex's `P1` on `38debbd`, thread
`PRRT_kwDOUAa7yM6jg6aS`; issue 139). Root cause: the wait asks "did Codex review this head",
while the condition the fallback needs is "did anyone the check trusts review this head" — the
read the verify step already makes on the workflow token's login, `github-actions`.

Reproduction: `tests/publisher/test_reusable_workflows.py::test_agent_review_waits_for_codex_falls_back_to_claude_and_enforces_threads`
asserts the wait names `--reviewer github-actions` beside the Codex login, and
`tests/publisher/test_request_codex_review.py` asserts `reviewed()` is true for either login
on the head — both red today. No platform observation precedes the fix (owner's decision,
2026-09-18): the platform fact the design rests on — `gh run rerun` re-executes every step —
is observed (attempts 2 and 3 of `35267976560` ran the wait again); the second review is
what the callee's own two lines then do, and a test proves those. The fix is confirmed where
every callee change is: on the first fallback head re-run after the merge, recorded in ADR
0027.

Related, folded in because it is the same step and stays small (Codex's `P2` on `38debbd`):
after a successful resolve the thread leaves `--list`, so a failure of the rerun or of the
reply cannot be retried through `--thread`; the script says nothing about how to finish the
step by hand.

## What Changes

- `request_codex_review.py --wait`: `--reviewer` is repeatable; presence is a review of the
  head by any of the named logins. The callee's wait step names the Codex app and
  `github-actions`; the verify step keeps `--reviewer github-actions` alone.
- `resolve_review_thread.py`: a failure after the resolve names what is still undone in its
  error — `gh run rerun <run-id>` and the reply call with the comment id when the rerun
  failed, the reply call alone when the reply failed — so the operator finishes the step by
  hand instead of finding the thread gone from `--list`.
- ADR 0027: the same-path run of the merged callee on this PR (the placeholder `<observed on
  the next PR>`), and the decision that a consequence of the callee's own lines is proved by
  a test, not observed on the platform first.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `review-and-merge`: "Codex reviews on the author's request, Claude is the fallback" — the
  wait reads presence for the Codex app or the workflow token's login; a re-run of the head's
  run after the fallback reviewed the head is enforcement alone.

## Impact

- Edited: `.github/workflows/reusable-agent-review.yml` (the wait step),
  `.agent-process/scripts/request_codex_review.py`,
  `.agent-process/scripts/resolve_review_thread.py`,
  `tests/publisher/test_reusable_workflows.py`,
  `tests/publisher/test_request_codex_review.py`,
  `tests/publisher/test_resolve_review_thread.py`, ADR 0027, `openspec/specs/` (by the
  archive alone).
- The callee change is not exercised by this PR's checks (the caller pins `@main`); the
  acceptance "no second Claude review on a fallback head" is observed on the first fallback
  head re-run after the merge and recorded in ADR 0027 then.
