---
status: "accepted"
date: 2026-08-23
decision-makers: ekolvah
---

# A required review verdict needs inspectable structured evidence

## Context and Problem Statement

The required `agent-review` check previously accepted an outcome-only Claude
payload. A payload such as `{"outcome":"blocking"}` made the check red without
showing a finding or proving what the reviewer examined. That spent fixer rounds
without an actionable defect.

## Considered Options

* Keep an outcome-only result and rely on optional review comments.
* Require structured findings but publish no durable summary.
* Validate conditional findings and publish the validated evidence in the check summary.

## Decision Outcome

Chosen: **validate conditional findings and publish them in the check
summary, and — when the Claude fallback is the carrier — also as a sticky
PR-conversation comment**. `clean` explicitly has no findings. `rework` and
`blocking` each require at least one finding with severity, confidence, and a
human-readable summary. The summary includes the live reviewed head SHA, so
an operator can relate the verdict to the exact diff.

Both review carriers produce that same evidence shape. GitHub-review carriers
place the JSON in a delimited HTML comment; the adapter also checks that its
declared outcome matches the review state GitHub recorded. The Codex primary
already leaves its own native GitHub review, so only the Claude fallback
additionally publishes a plain PR-conversation comment (never a
`REQUEST_CHANGES`/`APPROVE` state) — keyed on the reviewed head SHA so a
re-run updates it in place instead of duplicating it.

### Consequences

* Good, because a merge-blocking result is inspectable from the required check.
* Good, because malformed or incomplete Claude output becomes unavailable
  evidence and permits the existing second carrier to be attempted.
* Good, because the Claude fallback's findings are visible directly on the
  PR, not only in the Actions run summary.
* Good, because a new trusted-script capability is guarded by feature
  detection (a marker grepped from the trusted checkout) and skips with a
  notice when the default branch has not caught up yet, instead of failing.
* Bad, because carrier output outside the schema deliberately leaves the check
  red rather than guessing at a finding.

### Confirmation

`tests/test_agent_review_outcome.py` covers the conditional cardinality,
summary output, and PR-comment publish/dedup behavior.
`tests/test_reusable_workflows.py` checks the workflow schema, summary
wiring, and the PR-comment step's gating.
