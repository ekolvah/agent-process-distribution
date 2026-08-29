---
status: "accepted"
date: 2026-08-28
decision-makers: ekolvah
---

# The diff-stage review gate blocks two narrow §VII simplicity triggers

## Context and Problem Statement

`principles.md` §VII claimed "a diff-stage automated review then reviews the
actual PR as a second pass" for over-complication. The actual causal chain for
the enforced primary carrier did not support that claim: `REVIEW_CONTRACT.md`'s
look-for list never mentioned unnecessary complexity or reinvented
functionality, so Codex had no instruction to grade it above a low native
P-number, and even a caught finding landed `should-fix`/`nice-to-have` —
`NON-BLOCKING` by construction. The `blocking` prose definition only governs
the Claude fallback carrier's self-graded severity directly; it does not reach
Codex, the primary carrier on almost every PR, which grades from its own
native P0–P3 token consumed by `scripts/request_codex_review.py` and
`scripts/check_blocking_review_threads.py`.

The plan-stage architect review already reads the goal function and §I–VII,
but it reviews the *plan*, before implementation code exists, so it cannot see
bespoke code an implementer adds beyond the plan. That leaves a scope gap: the
only diff-stage carrier that could catch implementation-time over-engineering
had no instruction to grade it as blocking.

## Considered Options

* Leave `principles.md` §VII's claim as documentation-only and accept the gap.
* Correct `principles.md` to say diff-stage §VII enforcement does not exist.
* Add a full subjective "over-complicated" look-for item, blocking on Codex's
  and Claude's judgement call.
* Add exactly two narrow, worktree-verifiable triggers as blocking, keep every
  broader simplicity opinion advisory.
* Build a separate deterministic complexity-lint gate (e.g. cyclomatic
  complexity via radon/xenon).

## Decision Outcome

Chosen: **extend `REVIEW_CONTRACT.md` with an explicit look-for item plus a
Codex priority-assignment instruction and a symmetric Claude-fallback
`blocking` clause, limited to exactly two triggers**: (1) an added file,
class, wrapper, or dependency with a single call site and no stated reason for
the indirection; (2) duplicated logic whose finding names an existing symbol
and its repository-relative path. Both triggers are evaluable from the
checked-out worktree alone, never from PR-body text, which the contract
already forbids as merge authority. Every broader simplicity opinion
("this could be shorter") stays `nice-to-have`/advisory. `principles.md`
§VII's enforcement sentence is corrected to describe this narrow carve-out
accurately instead of claiming full diff-stage coverage.

A full subjective look-for item was rejected: blocking merge on "is this
over-engineered" invites false positives and merge friction, the same
over-engineering-from-chasing-findings failure mode §VII itself warns against.
A separate complexity-lint gate was rejected as new dependency and gate
surface duplicating an already-adopted external reviewer (§VII, goal 2).

### Consequences

* Good, because `principles.md` §VII's enforcement claim now matches what the
  gate actually does.
* Good, because reuse of the existing Codex/Claude-fallback contract avoids
  new tooling or a new CI job.
* Bad, because both triggers are payload files rendered into every consuming
  repository's merge gate with no per-project opt-out and no measured
  false-positive rate before rollout.
* Bad, because Codex grading a §VII finding sensibly once instructed is an
  assumption this repository cannot verify in advance.

**Assumption and rollback.** Assumes Codex's native P-number grading follows
the two named triggers accurately once instructed. Falsification signal: if
Codex's real P-number assignment on the first 5 PRs after merge shows a
disputed or false-positive rate the maintainer judges too high, revert the
priority-assignment instruction and keep only the look-for item
(should-fix-only), rather than iterating on trigger wording.

**Follow-up, out of scope here.** The fully-deterministic slice of the
indirection trigger (a new dependency addition) is a candidate for a
script-based gate instead of reviewer-prose instruction (§Scripts over
instructions) — not built in this issue.

### Confirmation

`tests/test_reusable_workflows.py::test_review_contract_and_principles_stay_coupled_on_narrow_simplicity_triggers`
guards that `REVIEW_CONTRACT.md` and `principles.md` §VII stay coupled: both
the enforcement sentence and the trigger definitions must be present together,
so removing either side reds the gate. Relates to
[ADR 0014](0014-review-gate-evidence-contract.md) (evidence shape both
carriers publish) and
[ADR 0015](0015-owner-requested-codex-primary-with-claude-fallback.md) (Codex
primary / Claude fallback carrier split) — this decision narrows what each
carrier is instructed to grade `blocking`, without changing either carrier's
selection or evidence contract.
