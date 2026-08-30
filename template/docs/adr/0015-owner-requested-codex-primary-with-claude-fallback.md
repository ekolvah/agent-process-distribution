---
status: "accepted"
date: 2026-08-24
decision-makers: ekolvah
---

# Owner-requested Codex review is primary with Claude fallback

## Context and Problem Statement

The prior workflow asked Claude first and attempted to trigger Codex by posting
`@codex review` with the workflow token. GitHub attributed that comment to
`github-actions[bot]`, which has no linked Codex account. Live PR evidence also
showed that an owner-requested Codex review uses standard GitHub inline P0-P3
comments rather than the repository's former private `agent-review-evidence`
JSON block.

GitHub Actions therefore cannot impersonate the connected repository owner,
and the gate needs to consume Codex's native review format without weakening
current-head or evidence validation.

## Considered Options

* Keep Claude first and let GitHub Actions post `@codex review` as fallback.
* Enable Codex Automatic reviews for every push.
* Use `openai/codex-action` with a separately billed API key.
* Let the PR author request Codex and retain Claude only as an availability
  fallback.

## Decision Outcome

Chosen: **the authenticated PR-author session requests `@codex review`; Codex
is the primary carrier, and Claude remains the fallback**.

The workflow never posts the Codex command or enables Automatic reviews. It
waits for Codex's standard GitHub review on the current PR head and translates
native priorities into the shared contract: P0/P1 are blocking, P2 is
should-fix, and P3 is nice-to-have. The observed clean connector comment is
also a narrow accepted transport only when its configured reviewer identity,
one of two exact supported observed shapes — a known `Codex Review`
clean-marker first line with one SHA-bound 10-hex `**Reviewed commit:**`, or
`No findings.` with one full `Reviewed head SHA:` — plus an eligible owner
request and
head/request/comment timestamps all bind it to the current head. The gate
orders valid native reviews, clean reactions, and clean comments by GitHub
timestamp, with the stricter non-clean outcome winning an equal-time tie; no
arbitrary bot prose can infer a clean result. A malformed current-head native
review invalidates older clean transports instead of reviving a stale result.
A valid Codex verdict is final for that head, including when the PR changes
agent-process policy files. Only missing, stale, or malformed Codex evidence
invokes Claude.

The default branch still owns parsing, outcome enforcement, and the required
workflow contract where the installed version is available. Human-only merge
and the platform workflow-definition trust anchor remain independent barriers;
Claude is not a mandatory second opinion on a valid Codex review.

### Consequences

* Good, because the delivery command posts the supported trigger through the
  authenticated owner session, without a paid OpenAI API route or a workflow
  bot identity.
* Good, because one valid review is enough and a substantive Codex result cannot
  be overridden by a second model.
* Good, because Claude still provides availability failover when Codex produces
  no usable current-head evidence.
* Bad, because every PR head that needs Codex review requires a new owner
  comment; the delivery flow must issue it after every successful push.
* Bad, because the first installation cannot obtain its parser from the default
  branch until the payload has merged, so that transition needs an explicit
  bootstrap path.

### Confirmation

`tests/test_request_codex_review.py` covers owner-session dispatch, native
priority translation, current-head binding, clean owner reactions, the
SHA-bound clean-comment transport, timestamp precedence, and malformed evidence.
`tests/test_reusable_workflows.py` checks that Codex is primary, Claude runs
only after invalid or unavailable evidence, and enforcement executes from the
trusted checkout.
