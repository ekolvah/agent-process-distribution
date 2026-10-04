## Context

See proposal.md — Why. The planner reads the skill's Principles section; the
`architect-reviewer` reads `principles.md` from the skill directory and `openspec/config.yaml`.

## Goals / Non-Goals

**Goals:** `principles.md` carries every generic statement the consumer copy has, so the
consumer can delete its copy.

**Non-Goals:** the consumer's documentation refactor; its Evidence block and `discovery`
subagent, which the `planning` spec keeps out of the core ("No per-label section sets and no
discovery role").

## Decisions

**D1 — One principles file, no extension point.** Agent-process principles live in the plugin;
product facts stay in the consumer's product documents. A second normative file of the same
name invites the drift #316 reports and splits the canon. `principles.md` already defers each
product fact to a project document, so nothing in the consumer copy needs a principles-shaped
home. Alternatives: `openspec/principles.md` read beside the core (planned first, reviewed to
`approve`) — declined by the person: two principles files confuse, and it needed `roles` and
`distribution` deltas; inline in `config.yaml` `context` — rides on every
`openspec instructions` call (ADR 0027: 20 695 bytes per call against 6 829 with a short one).

**D2 — What goes upstream.** From the consumer's diff and its governance conventions:

| Consumer statement | Outcome |
| --- | --- |
| §V: failing and exact valid record from one captured response; a sibling source does not count | `principles.md` §V |
| §V: compare boundaries broad to narrow; losing the valid record needs a product decision; trace the call path before claiming a new fetch | `principles.md` §V |
| Quality Gates: ruleset, up to date, both required contexts, no bypass actors; P2/P3 answered before merge | `principles.md` Quality Gates as a pointer to the ruleset, replacing "All CI checks are green" and the "not enforced" bullet: a restated copy of the gate facts is what drifted |
| Consumer convention 1: temporary CI unblock only with a tracked root-cause issue | `principles.md` §V, folded into the "documented mitigation … with a linked issue" example (one-PR-one-unit is already goal 3); not a new Governance rule, because procedural rules live in the skill and the specs |
| Consumer convention 6: a trivial non-behavioural one-liner may skip the change workflow with recorded rationale | Not taken: covered by `planning` "Substantive work SHALL start as an OpenSpec change" and §I exception (c) |
| Consumer convention 2: one type label per issue | Not taken: the person judged it obsolete |
| Consumer conventions 3–5: priority script, `pip-compile`, no push to `main` | Not taken: product-specific, or already the skill's Delivery and the ruleset |
| Product names in §II, §III, §IV, §V, §VI; `evidence/<change>/`, capture scripts; §VII decision against a third-party plugin; Scripts-over-instructions precedent | Product facts: the consumer's product documents or ADRs |

Planned wording, `principles.md` §V, in its first paragraph after "repository reasoning alone
is not evidence." — scoped to observing a live external system, and introducing the valid
record the next paragraph names: "The observation names the failing record and an exact valid record from the same
captured response; a sibling feed, query or source does not stand in for it. Compare candidate
fix boundaries from broad to narrow: one that loses the valid record needs an explicit product
decision. Trace the current call path before claiming that a narrow fix needs another fetch."

Quality Gates, first bullet: "The ruleset that `activate_protection` installs passes." The
"automated PR review … not enforced" bullet becomes: "Unresolved review threads the check
passes (`P2`/`P3`, or another author's) are answered in PR comments before merge; the person
merging holds this, no check does."

§V mitigation sentence: "(e.g. raise-and-skip with a linked issue)" becomes "(e.g.
raise-and-skip, or a temporary unblock of an unrelated CI failure, with a linked issue for the
root cause)".

## Risks / Trade-offs

- [A consumer needs a rule the core lacks] → it goes upstream through an issue, as #316 did;
  no local canon to drift.

## Migration Plan

Text only. Rollback is a revert of the PR.
