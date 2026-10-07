## Context

See proposal.md — Why. The job's close step (added by `job-closes-claude-review`, #349) fails
unless `steps.claude.outputs.conclusion` is `success` and then posts
`Reviewed head SHA: <sha>`; `head_review.py` reads that marker with `re.search` and the
enforcement reads only inline `P0`/`P1` threads. ADR 0027 holds that nothing of ours reads
what a review says; the v2-2b guard `"--json-schema" not in claude_args` keeps review
outcomes out of a schema.

Observed in `anthropics/claude-code-action@v1` (5898584, 2026-10-06):

- `base-action/src/execution-file.ts` writes every SDK message to
  `$RUNNER_TEMP/claude-execution-output.json`; `run-claude-sdk.ts` writes it before it sets
  `conclusion`, and `src/entrypoints/run.ts` sets the `execution_file` output
  (`core.setOutput("execution_file", claudeResult.executionFile)`) on the success path.
- `run-claude-sdk.ts` logs, without `show_full_output`, only the result summary with
  `permission_denials_count`; the denials themselves and the final text stay in the file.
- The result message of a session with a denied call (local probe in proposal.md — Why) is
  `subtype: success, is_error: false`, with the final text in `result` and each denial as
  `{tool_name, tool_use_id, tool_input}` in `permission_denials`.

## Goals / Non-Goals

**Goals:** the closing comment shows what the session says it read, found and did not verify,
and every denied call; a session that ends without a final message fails the check.

**Non-Goals:**
- Changing `--allowed-tools` or pinning `--model`. The local replay with the CI allowlist and
  `claude-sonnet-5-5` read past the diff and reached a substantive verdict, so neither is the
  observed cause. The denied CI calls this change publishes decide the allowlist in a follow-up
  issue; the model is a cost decision for the person.
- Checking the final message's claims (files read, scope). Nothing of ours judges review
  content (ADR 0027).

## Decisions

### D1. The closing comment carries the session's final message and denials

The close step keeps its `conclusion` check, then builds the comment from the action's
`execution_file`: the marker line `Reviewed head SHA: <sha>` first, the last result
message's `result` verbatim, then `Permission denials: <n>` and one line per denial — the
tool name and its `command`, or its compact `tool_input` when it has no command, JSON-encoded
so a multi-line command stays on its line. The marker
stays the first line so `head_review.py`'s `re.search` matches it before any text the model
wrote; `head_review.py` is unchanged and a head closed under the old format still reads as
reviewed.

Alternatives rejected:
- *`--json-schema` verdict (`{verdict, files_read[]}`)* — the action does fail without it,
  but its fields are the model's own assertion like the final message, it puts the review
  outcome back into a schema (v2-2b guard, ADR 0027), and it drops the free-text "Not verified"
  list the replay produced.
- *`show_full_output: true`* — prints every message and tool result to the public log; the
  action's input description warns it may expose secrets.
- *`display_report: true`* — writes Claude-authored turns to the step summary, off the PR, with
  the same warning.

### D2. `close_review.py` reads the execution file

Problem: #363. New `.agent-process/scripts/close_review.py --execution-file <path>
--head-sha <sha> --body-file <out>`, run from the trusted checkout like `head_review.py`:
exit 0 writes the D1 body; exit 1 with `::error::`
and no body when the file is missing or not a JSON list, has no `result` message, or its
`result` is empty or whitespace. The step then runs
`gh pr comment "$PR" --repo "$REPO" --body-file "$RUNNER_TEMP/review-close.md"`, with
`EXECUTION_FILE: ${{ steps.claude.outputs.execution_file }}` in `env`.

Standard considered: `jq` in the step (preinstalled on `ubuntu-latest`). Rejected: the close
step's test runs its `run` under Git Bash on the developer's Windows machine, where `jq` is
absent (`jq: command not found`), and the empty-result and missing-file branches need tests
of their own; Python is already the job's language for its readers.

### D3. Denials are published, never fail

A denial is not an absent review — the probe ends `success` with a final message — and a
failure on it would turn every consumer PR red, each re-run paying for a session that hits the
same denial until the allowlist changes. The catcher is the closing comment on the PR, which
the person reads before merging. No `::warning::` annotation: the command is model text the
PR can steer, and an unescaped newline in a workflow command line starts a new command. Failing on denials becomes
reasonable once the allowlist follow-up grants what the contract needs.

### D4. The model ends with a final message

The prompt adds: end the session with a final message naming what you read, the findings you
posted, and what you did not verify; the job publishes it in the closing comment. "No other
comment" stays — the final message is not a comment the model posts. The duty lives in the
prompt only, where the workflow test anchors it; `REVIEW_CONTRACT.md` already says the job
posts the closing comment. ADR 0027 gains a More Information bullet: the job republishes the
final message and gates on its presence, never on its content.

## Risks / Trade-offs

- [The action renames `execution_file` or the result message's fields] → the script exits 1,
  every review turns red at the close step, never green.
- [The final message comes from a session steered by PR content] → it is published under the
  workflow token as the model's text below the marker; it decides nothing, the gate still reads
  only threads. A forged marker line in it follows the real one, which `re.search` finds first.
- [A final message over GitHub's 65,536-character comment limit] → `gh pr comment` fails and
  the check is red, visibly; not observed (the replay's message was a few paragraphs). A cap
  waits for an occurrence.
- [A session ends with only tool calls] → red check and a paid re-run; the prompt asks for the
  final message, and this is the silent finish #363 asks to stop counting as clean.

## Migration Plan

This repository's caller pins `@main`, so the PR's own heads run the old close step; the new
one first runs on the first PR reviewed after merge. Release PRs skip the review (ADR 0031),
so nothing stops a release before that; the PR body and the final report ask the person to
merge the next release PR only after a reviewed PR's closing comment shows the final message. The denials named on the first consumer
closing comments open the allowlist follow-up issue. Rollback: revert the PR; the marker line
is unchanged, so heads reviewed under either version read as reviewed under the other.
