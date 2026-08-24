---
status: "superseded by ADR-0016"
date: 2026-08-24
decision-makers: ekolvah
---

# Subscription-backed automatic Codex review is the primary review carrier

## Context and Problem Statement

The prior workflow asked Claude first and attempted to trigger Codex by posting
`@codex review` with the workflow token. GitHub attributes that comment to
`github-actions[bot]`, which has no linked Codex account; the required check
then waits without obtaining a fallback verdict. Codex's GitHub integration can
instead create automatic reviews through the maintainer's ChatGPT subscription.

## Considered Options

* Keep Claude first and post `@codex review` from Actions.
* Use `openai/codex-action` with an API key.
* Add a second required status context for Codex.
* Wait for automatic Codex review first, then use Claude only for unavailable
  or invalid Codex evidence.

## Decision Outcome

Chosen: **automatic Codex review first, Claude availability fallback second**.
Maintainers enable Codex Automatic reviews with the **On every push** trigger.
The workflow only reads and polls current-head reviews from
`chatgpt-codex-connector[bot]`; it never posts `@codex review`. A valid Codex
`clean`, `rework`, or `blocking` payload is final for that head. Only missing
or invalid evidence invokes Claude, and both paths use the same trusted
validator and durable reviewed-head summary.

### Consequences

* Good, because the primary carrier uses the existing ChatGPT subscription and
  needs neither `OPENAI_API_KEY` nor a maintainer GitHub token.
* Good, because a substantive Codex `blocking` result cannot be masked by a
  second carrier.
* Bad, because the required check waits for the bounded automatic-review window
  before Claude can handle an unavailable Codex review.
* Bad, because the external Automatic reviews setting cannot be proven by local
  tests; a two-head live smoke test remains required before distribution.

### Confirmation

`tests/test_request_codex_review.py` verifies that the adapter never posts a
request and accepts only the current head. `tests/test_reusable_workflows.py`
checks the carrier order and failover conditions. A representative PR and one
subsequent push must each receive a Codex review tied to their respective head.
