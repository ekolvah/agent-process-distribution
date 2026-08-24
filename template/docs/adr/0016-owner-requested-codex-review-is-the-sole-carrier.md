---
status: "accepted"
date: 2026-08-24
decision-makers: ekolvah
---

# Owner-requested Codex review is the primary required-review carrier

## Context and Problem Statement

ADR-0015 assumed Codex Automatic reviews would produce a custom structured
payload. Live PR evidence showed that the supported `@codex review` request from the PR author produces a
standard GitHub review with inline P1/P2 comments, while the adapter rejected it
because no private `agent-review-evidence` block existed. It then waited for its
full timeout before a Claude fallback failed without structured output.

GitHub Actions must not post `@codex review`: that comment is authored by
`github-actions[bot]`, not the repository owner who connected Codex. The owner
request is the explicit external authority for the review. The default branch
still owns parsing, outcome enforcement, and branch-protection policy; this does
not make PR-controlled review guidance a platform trust anchor.

## Considered Options

* Keep Automatic reviews as the Codex trigger.
* Let GitHub Actions post `@codex review` with its workflow identity.
* Use the PR author's manual `@codex review` as primary and retain Claude fallback.

## Decision Outcome

Chosen: **the PR author manually requests `@codex review`; Codex is the primary
carrier and Claude remains the fallback**.

The caller begins on each PR head and waits only for that native Codex review.
It never writes a trigger comment or enables Automatic reviews. It retains the
Claude credential and invokes Claude only when Codex leaves no valid evidence.
After this transition the adapter, validator, and
enforcement run from the default-branch `trusted/` checkout. The introducing PR
has a visible bootstrap fallback only because its default branch cannot yet
contain the new parser; the default-branch validator still validates its output.
The adapter reads the review and its inline comments:
P0/P1 map to `blocking`, P2 to `should-fix`, and P3 to `nice-to-have`. The
trusted default-branch validator publishes structured evidence from those native
records. A missing, malformed, or stale review remains red.

### Consequences

* Good, because the supported owner-authored trigger is visible and auditable on
  the PR, and an arriving native review ends the wait immediately.
* Good, because Codex's actual P1/P2 findings become inspectable gate evidence
  rather than being discarded for lacking a private JSON envelope.
* Bad, because each reviewed PR head needs an owner comment to receive the
  Codex primary review; without it the slower Claude fallback is used.
* Bad, because the manual request is review evidence, not an alternative to an
  external workflow-definition trust anchor or a human decision on policy-file
  changes.

### Confirmation

`tests/test_request_codex_review.py` covers P1/P2 translation, current-head
matching, and immediate rejection of a malformed current-head review.
`tests/test_reusable_workflows.py` asserts that Claude runs only after no valid
Codex evidence and that trusted enforcement is separate from the PR-head adapter. A PR
author requests `@codex review` on the opening head and a subsequent pushed head
before the required check is handed off.
