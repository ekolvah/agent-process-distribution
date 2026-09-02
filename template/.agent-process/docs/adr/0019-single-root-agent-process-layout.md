---
status: "accepted"
date: 2026-09-01
decision-makers: ekolvah
---

# Every process-owned path renders under `.agent-process/`, with a closed, named exception set

## Context and Problem Statement

ADR-0018 decided the distribution owns only `.agent-process/**` and
`.github/workflows/agent-process-*.yml` as complete files; `stage_payload()`
kept a path only when it matched `_ALLOWED_PREFIXES`, archiving everything
else to the inert `.agent-process/payload/`. That allowlist answered "could
this path collide with consumer-owned content?" — not "does the process's own
code dereference this exact root-relative path at runtime?". The two
questions differ, so every process-owned file outside the allowlist was
silently archived while the code that needed it — `ci_check.py`'s
`requirements*.txt` reads, the reusable workflows' `trusted/scripts/...` and
`pr/requirements*.txt` references, `AGENTS.md`, `REVIEW_CONTRACT.md` — kept
looking at the root. Nothing failed loudly: the archive write succeeded, so
adoption reported success while most of the functional surface was missing.
The allowlist had already grown from ADR-0018's two entries to seven by the
time this was found, an open-ended class rather than a bounded exception.

## Considered Options

* Keep growing `_ALLOWED_PREFIXES` as each missing dereference surfaces.
* Add `_skip_if_exists` or fatal-on-archive to make the gap visible without
  removing it.
* Relocate every process-owned path under one reserved root
  (`.agent-process/`) except a small, closed, individually-justified set that
  cannot move for external reasons.

## Decision Outcome

Chosen option: relocate under one reserved root. Every process-owned file
renders under `.agent-process/`, except a closed root set — none of its
entries may move, and each is justified individually rather than by a
directory-wide exemption:

* `.github/workflows/ci.yml`, `.github/workflows/agent-review.yml`,
  `.github/workflows/pr-link.yml` — GitHub Actions only discovers workflows
  under `.github/workflows/`; kept under their real names rather than
  renamed to an `agent-process-*.yml` pattern (a rename is a separate,
  out-of-scope change).
* `.github/pull_request_template.md` — GitHub only reads this from
  `.github/`, the repository root, or `docs/`.
* `.claude/**`, `.codex/**`, `.agents/**` — tool-mandated adapter roots; each
  agent harness looks for its own configuration at a fixed path it does not
  let the process relocate.
* `AGENTS.md`, `.gitignore` — managed-fragment targets: a consumer's own
  content coexists with the process's delimited fragment in the same file.
* `tests/agent_process/` — the ADR-0017 reserved consumer-test subtree; a
  process conformance test is not itself `.agent-process/`-owned code, but it
  still cannot live at an arbitrary consumer path.

`pyproject.toml`, `.copier-answers.yml`, and `.gitattributes` are explicitly
**not** in the closed set: they move under `.agent-process/` like everything
else. `stage_payload()` and `_ALLOWED_PREFIXES` are deleted, not retained
disabled — `.agent-process/payload/` no longer exists in any render.

A publisher test generalizes the byte-identity collision check
`check_consumer_test_collision.py` already implemented for the single
`tests/agent_process` reserved subtree (ADR-0017): the same check now
retargets to this decision's closed root set, so adopting into an established
repository that already owns `scripts/`, `docs/`, `tests/`, `requirements.txt`,
`pyproject.toml`, and `AGENTS.md` leaves every one of those byte-identical
instead of two independent implementations of the same collision rule
drifting apart. [ADR-0017](0017-publisher-tests-stay-in-source-consumers-get-a-reserved-subtree.md)
is updated to describe this generalized scope rather than the single-subtree
form it originally recorded.

This decision supersedes [ADR-0018](0018-established-project-adoption-uses-reserved-paths.md):
where ADR-0018 reserved two prefixes and let every other process path stay at
the consumer root, this decision reserves one root and lists the exceptions
instead, closing the open-ended allowlist-growth class at its cause rather
than at each symptom.

**No migration path.** No adopter exists yet on the pre-`.agent-process/`
layout — the prior code implementing ADR-0018 never merged to `main` (its PR
was closed as superseded by this decision, not shipped). This decision
therefore defines no `copier update` migration from the old layout; only a
fresh `copier copy` is supported going in.

### Consequences

* Good, because every process-owned path a consumer might collide with is
  either under one reserved root or in a short, individually-justified,
  testable exception list — the allowlist-growth class this record replaces
  cannot silently recur without a new closed-set entry showing up in review.
* Good, because a single generalized collision check protects both the
  ADR-0017 test subtree and this decision's closed root set, instead of two
  implementations that can drift apart.
* Bad, because every existing process script, doc, hook, and workflow
  reference that pointed at the pre-migration root-level script and
  architecture-doc locations needed a one-time rewrite to their
  `.agent-process/`-relative paths — a migration cost this record accepts
  once rather than amortizing across every future path addition.

### Confirmation

`tests/publisher/test_payload_layout.py` asserts every rendered path outside
`.agent-process/` is a member of the closed root set above, including nested
additions inside an allowed directory. `tests/publisher/test_template_drift.py`
confirms this repository's own self-applied root matches a fresh render of
the same template. `.agent-process/scripts/check_consumer_test_collision.py`
confirms an established-project fixture adopts cleanly with every
pre-existing closed-root-set file left byte-identical.

## More Information

Relates to [ADR-0011](0011-agentic-process-distribution-mechanism.md) (the
Copier distribution mechanism this layout rides on), [ADR-0012](0012-ci-logic-is-referenced-not-copied.md),
and [ADR-0017](0017-publisher-tests-stay-in-source-consumers-get-a-reserved-subtree.md)
(generalized by this decision, see above).
