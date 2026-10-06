## Context

See proposal.md — Why. The job has three review steps today: a presence read of the closing
comment (`head_review.py --wait --timeout-seconds 0`), the `Claude review` action whose
prompt asks the model to post that comment with `gh pr comment`, and a bounded presence read
(`--timeout-seconds 60`). Two constraints bind the fix: nothing of ours parses a review
(ADR 0027), and the action can finish green without invoking the model (ADR 0004:
`Skipping action due to workflow validation`), so "the action step succeeded" alone is no
proof of a review.

## Goals / Non-Goals

**Goals:** a review that ran to its end always yields the closing comment; a review that did
not still fails the check.

**Non-Goals:** surfacing an unlabelled inline comment of the review job as a contract
violation (the issue's last sentence). After this change the model is no longer asked for a
closing note, which is what it misplaced; a new gate on unlabelled threads waits for an
observed recurrence. The two stray threads on kinozal_scraper#629 are the person's to
resolve.

## Decisions

### D1. The action's `conclusion` output is the end of the review

The job posts the closing comment when `steps.claude.outputs.conclusion` is `success`.
Observed in `anthropics/claude-code-action@v1` (cab360f):

- `action.yml` output `conclusion`: "Execution status of Claude Code ('success' or
  'failure')".
- `src/entrypoints/run.ts`: `core.setOutput("conclusion", claudeResult.conclusion)` runs
  only after `runClaude` returns. The skip paths return before it — `WorkflowValidationSkipError`
  (`"Exiting due to workflow validation skip"`, the ADR 0004 case) and `"No trigger found,
  skipping remaining steps"` — so there the output is empty.
- `base-action/src/run-claude-sdk.ts`: `result.conclusion = isSuccess ? "success" :
  "failure"`, `isSuccess` being `resultMessage.subtype === "success" && !resultMessage.is_error`
  — the session ended normally; otherwise it throws `Claude execution failed: …`, `run.ts`
  calls `core.setFailed` and never sets `conclusion`. The action thus emits `success` or
  nothing.

So `success` proves the model ran the review to its end, which is exactly what the
model-posted closing comment proved, without depending on which tool it chose. The job reads
no content of the review (ADR 0027).

Alternatives rejected:
- *`--json-schema` structured output as the finishing signal* — the action fails without it,
  but it proves no more than `conclusion` does, adds a schema field nothing reads, and drops
  the v2-2b guard `"--json-schema" not in claude_args` that keeps review outcomes out of a
  schema.
- *Bounded automatic re-run* when inline comments exist without a closing comment — pays a
  second review and depends on the same compliance a second time.
- *Posting whenever the action step succeeds* — loses the ADR 0004 guard: a skipped action is
  green with no model invocation.
- *Reading the inline comments to decide* — parses the review (ADR 0027).

### D2. The job posts the closing comment in a workflow step

A new step `Close the Claude review of the head`, between `Claude review` (given
`id: claude`) and the unchanged `Verify the Claude review of the head`, runs under the same
`absent == 'true'` condition, so a skipped action reaches it: `test "$CONCLUSION" = success`
or `::error::` naming the conclusion and exit 1, then
`gh pr comment "$PR" --repo "$REPO" --body "Reviewed head SHA: $SHA"`. Every value comes in
through `env`, none is interpolated into the script. The workflow token posting the comment is
the one the model's `gh pr comment` used, so the author is `github-actions[bot]`, the login
`head_review.py` accepts — observed on the re-run of run 37339592131, whose comment turned the
check green.

Two shell commands do not earn a script (§VII). The body's agreement with `head_review.py`'s
`_REVIEWED_HEAD` is tested by feeding the body the step posts to `head_review.reviewed`. The
bounded read stays: it proves the comment is readable the way the pre-review read will read it
on a re-run.

### D3. The contract and prompt lose the closing-comment duty

`Bash(gh pr comment:*)` leaves `--allowed-tools`. The prompt and the publication bullet of
`REVIEW_CONTRACT.md` say: one labelled inline comment per finding and no other comment; the
job posts the closing comment when the review ends. The `No findings.` prefix goes: the job
does not know the count and does not read it.

No ADR: ADR 0004's guard and ADR 0027's no-parsing rule both hold; the decision lives here.

## Risks / Trade-offs

- [The model hits its turn limit or errors] → the `Claude review` step itself fails with
  `Action failed with error: Claude execution failed: …`; the close and verify steps are
  skipped, the enforcement runs under `always()`, the check is red, and a re-run reviews
  again — the visible outcome an interrupted review has today. The close step's test of any
  conclusion but `success` covers a future action that reports `failure` without failing.
- [The action renames or drops `conclusion`] → the output reads empty, every review turns red
  at the close step, never green.
- [A finding posted with no label] → unchanged: the enforcement reads only `P0`/`P1`.

## Migration Plan

This repository's caller pins `@main`, so the PR's own heads run the old job and the new path
first runs on the first PR reviewed after merge; that run must be green before the next
release ships it to consumers, who get it when their caller's pin moves. Rollback: revert the
PR; the closing-comment format is unchanged, so heads reviewed under either version read as
reviewed under the other.
