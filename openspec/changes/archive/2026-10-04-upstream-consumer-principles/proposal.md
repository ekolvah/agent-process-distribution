## Why

A consumer keeps its own copy of `principles.md` that no review reads, so it drifts (#316).
Observation, 2026-10-04: `ekolvah/kinozal_scraper` `docs/architecture/principles.md`, fetched
with `gh api …/contents/… -H "Accept: application/vnd.github.raw"` and diffed against
`skills/agent-process/principles.md`, has the same sections. Its differences are product facts
(Telegram, `sources.json`, `Storage`/`Notifier`/`Enricher`, its capture scripts), its own
decision records, and three generic statements the plugin lacks: the §V evidence bounds
(failing and valid record from one response, broad-to-narrow boundaries, trace the call path
before claiming a new fetch) and Quality Gates that name the ruleset. The plugin's own Quality
Gates is wrong for every consumer: it says "a hard block on its verdict is not enforced", while
the ruleset `activate_protection` installs requires `agent-review / agent-review`
(`distribution` spec, "A context the PR cannot change gates every head"), which fails on an
unresolved `P0`/`P1` thread (`review-and-merge` spec, "Unresolved P0/P1 threads fail the review
check").

## What Changes

- `principles.md` takes the generic statements: the §V evidence bounds, Quality Gates pointing
  to the installed ruleset, and in §V's documented mitigation the consumer's temporary CI
  unblock with a linked root-cause issue.
- One principles file: the plugin's. A consumer keeps no principles of its own; its product
  facts belong in its product documents, which `principles.md` already defers to (§II's
  project-local runtime document, §V's capture "the target project does", the gate
  configuration and coverage-gaps ledger of "Not here"). The requested extension point is
  declined (#316; the person's decision, design D1).
- Not taken: the consumer's type-label taxonomy (the person's decision: obsolete, the consumer
  deletes it); its one-line-skip convention, already covered (design D2).

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- Edited: `skills/agent-process/principles.md`. No spec delta (`skip_specs`): no requirement
  changes; the text is principle prose (§I documentation exception).
- Added, removed: none. No ADR: the decision and its alternatives are in `design.md`.
- Consumer side, outside this change (kinozal_scraper roadmap epic): move product facts into
  its product documents, delete its `principles.md` and the governance section, retarget or
  close its principles issue (#601).
