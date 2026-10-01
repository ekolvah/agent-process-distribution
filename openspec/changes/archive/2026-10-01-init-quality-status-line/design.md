## Context

See proposal.md — Why. `init`'s output has three kinds of line: step transitions
(`<status> <label>: <detail>`, for what `init` writes), `manual` rows (actions only a UI, the
machine or the clone can take, from `manual.rows`), and the plan's preface lines
(`repository: …`, `planned hand-off: …`). The quality line is built in `_manual`, outside
`manual.rows`, and prepended to them.

## Goals / Non-Goals

**Goals:** a `manual` row is always an action; the missing declaration stays visible on every
run where it is missing (§IV).

**Non-Goals:** changing when the declaration counts as valid (`_test_declared`), or what
`init` writes.

## Decisions

- **D1 — a `quality:` status line before the `manual` rows.** `_manual` returns only
  `manual.rows`; `run` itself prints, while `_test_declared(ctx.root)` is false, the line
  `quality: <declaration> declares no test -- CI runs no tests until the change that adds the
  first tests declares {"test": "<command>"}` after the transitions and before the `manual`
  rows (inline: one call site, no helper), so the requirement that the `manual` rows end the
  output still holds; with every state observed done there are no `manual` rows and it holds
  vacuously.
  Alternatives: a step transition (`unchanged quality-command: …`) — rejected, transitions
  describe files `init` owns and `unchanged` would read as "nothing to see"; dropping the line —
  rejected, a missing quality command would become silent (§IV); keeping the row and adding
  "no action" to its text — rejected, the prefix still files it under actions in Install step 4
  and in `manual` row parsing.
- **D2 — Install step 4 drops the `quality-command` sentence.** Step 2 already shows the whole
  output, so the status line reaches the person; step 4 lists only what to tell the person to
  do. `test_install_asks_no_quality_command` flips to assert the Install section no longer
  names `quality-command`; Install step 1 ("Ask for no quality command") stays.

## Risks / Trade-offs

- [A consumer script greps `manual quality-command`] → none is known: the row is read only by
  the agent relaying the output and by this repository's tests, which this change updates.

## Migration Plan

None: the next release's `init` prints the new line. Rollback is reverting the PR.
