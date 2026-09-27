## Context

Four text leftovers found by the 2026-09-27 audit (proposal **Why**). None is read by a script
or pinned by a requirement.

## Decisions

### D1. No new test

The move is guarded by the existing `tests/agent_process/test_doc_links.py`, which resolves every
relative link of every tracked Markdown file (`git ls-files`): a wrong link after the move is
red there. The other three edits change prose and a manifest display name; a test that forbids
one specific string would pin this audit, not an invariant (§VII). The task list records
`no RED: <reason>`.

Alternative rejected: a test that no tracked file names `kinozal_scraper maintainers`. It
catches only the string it was written for.

### D2. The revision condition keeps its rule without a named measurer

`navigation_policy.py` states when to revisit the read-size rule. The measurer it names does not
exist; inventing one is out of scope (ADR 0029 moved telemetry out of v2). The sentence keeps the
condition — refusals that do not reduce context growth before the first edit mean tighten or
revert — and drops the file name and "do not build a second measurer", which only refers to it.

### D3. The document moves to `.agent-process/docs/`, not `.agent-process/docs/adr/`

It is an owner-side setup document, not a MADR record; `test_adr_records.py` would reject it in
the ADR directory. Its links become `adr/0026-…` and `adr/0029-…`; ADR 0026's link becomes
`../telemetry-measurement-setup.md`.

## Risks / Trade-offs

- An external bookmark to `docs/telemetry-measurement-setup.md` on GitHub breaks. The document is
  owner-side; no consumer reads it.

## Migration / Rollback

One PR; revert restores every path and string.
