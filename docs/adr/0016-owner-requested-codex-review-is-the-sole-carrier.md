---
status: "accepted"
date: 2026-08-24
decision-makers: ekolvah
---

# Owner-requested Codex review is the sole required-review carrier

## Context and Problem Statement

ADR-0015 assumed Codex Automatic reviews would produce a custom structured
payload and used Claude when it did not. Live PR evidence disproved both
assumptions: the supported `@codex review` request from the PR author produced a
standard GitHub review with inline P1/P2 comments, while the adapter rejected it
because no private `agent-review-evidence` block existed. It then waited for its
full timeout and a Claude fallback failed without structured output.

GitHub Actions must not post `@codex review`: that comment is authored by
`github-actions[bot]`, not the repository owner who connected Codex. The owner
request is the explicit external authority for the review. The default branch
still owns parsing, outcome enforcement, and branch-protection policy; this does
not make PR-controlled review guidance a platform trust anchor.

## Considered Options

* Keep Automatic reviews and the Claude availability fallback from ADR-0015.
* Let GitHub Actions post `@codex review` with its workflow identity.
* Use only the PR author's manual `@codex review` and read the native review.

## Decision Outcome

Chosen: **the PR author manually requests `@codex review`; Codex is the sole
carrier**.

The caller begins on each PR head and waits only for that native Codex review.
It never writes a trigger comment, enables Automatic reviews, reads a provider
secret, or invokes Claude. After this transition the adapter, validator, and
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
* Bad, because each reviewed PR head needs an owner comment; an absent request is
  intentionally red.
* Bad, because the manual request is review evidence, not an alternative to an
  external workflow-definition trust anchor or a human decision on policy-file
  changes.

### Confirmation

`tests/test_request_codex_review.py` covers P1/P2 translation, current-head
matching, and immediate rejection of a malformed current-head review.
`tests/test_reusable_workflows.py` asserts that no Claude step or provider secret
remains and that trusted enforcement is separate from the PR-head adapter. A PR
author requests `@codex review` on the opening head and a subsequent pushed head
before the required check is handed off.
