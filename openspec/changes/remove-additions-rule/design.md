## Context

`architect-review.schema.json` requires `additions` (issue 170, ADR 0027): one entry per
script, check or non-test file, and under `approve` a `problem` matching an issue, PR or run
reference and a `standard` other than none, n/a or a dash. `create_tracking_issue.py` and
`start_change.py` validate the file against the schema; neither reads `additions` otherwise
(no code names the key outside the schema and the tests).

## Goals / Non-Goals

**Goals:** a plan without a prior issue validates without a filler reference; the justification
of a new script or check stays required, in the standard decision-record form.

**Non-Goals:** choosing a third-party anti-bespoke skill (Ponytail is the pilot of #9, after
this change); a new deterministic check.

## Decisions

**D1 — Remove `additions` from the schema.** Drop the property, its `required` entry and its
`then` constraint. `additionalProperties: false` stays, so a file carrying the key fails with
"Additional properties are not allowed ('additions' was unexpected)" — visible, not ignored.
The spec keeps the scenario "Addition without evidence" with this refusal as its outcome:
OpenSpec 1.13 rejects a MODIFIED delta that drops a scenario the main spec has (observation on
record: `openspec/changes/archive/2026-09-19-v2-2d-check-red-own-runner/design.md:87`; this
change's first `validate --strict` printed the same refusal).
Alternatives: (a) keep the list, drop only the `problem` regex — the list stays a bespoke
duplicate of the design decisions and still takes every non-test file; (b) create the tracking
issue before the review — the reference would be the change's own issue, proving nothing, and
the propose tail grows a step; (c) narrow the scope to process paths — keeps the regex that
checks form, not relevance.

**D2 — The `bespoke` class reads the design decision.** Its description becomes: "Each script or
check the plan adds and its design.md decision: the problem it closes and the standard for its
job and why it does not fit; a missing or unconvincing decision is a finding." Scope narrows
from "non-test file" to "script or check", the target of the rule (§VII). This is the MADR
"Considered Options" / Rust RFC "Rationale and alternatives" form, which OpenSpec `design.md`
already carries as Decisions.

**D3 — The Design procedure asks for it.** `SKILL.md` Design gains one bullet: a new script or
check has a decision naming the problem it closes — an issue, PR or run when one exists — and
the standard for its job and why it does not fit.

**D4 — ADR 0027 records the removal** as a bullet after the issue 170 entry it reverses.

### Dropped guard (D1)

- **Lost proof:** a machine check that each added script or check names a reference-shaped
  problem and a non-empty standard.
- **Failure mode it covered** (issue 170): the free-text `bespoke` class accepted `none`.
- **Catcher now reached:** the `bespoke` class of `architect-review.json`, written by the
  `architect-reviewer` subagent in every propose run before `create_tracking_issue` validates
  it; its evidence must name each script or check and its decision (D2), so `none` for a plan
  whose Impact adds a script is a finding the reviewer has to state against the listed file.
  Then the Claude review job of `agent-review` on each PR head, whose contract carries the §VII
  simplicity triggers, and the person's merge.
- **What stops proving:** that the reviewer's judgement is sound; the regex never proved that
  either — #117 step 7a passed it with `#1`.

## Risks / Trade-offs

- A review can again mark `bespoke` `ok` without substance. Mitigation is the evidence the
  class requires (each script or check by name); if a plan passes with an unjustified script,
  that observation is the problem a narrower deterministic guard (e.g. CODEOWNERS on process
  paths) would need.
- Migration: an in-flight change whose `architect-review.json` carries `additions` fails
  validation naming the key; the reviewer rewrites the file without it. Rollback is reverting
  this PR.
