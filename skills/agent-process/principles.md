# agent-process-distribution architectural principles

**Question this document answers:** which principles, workflow rules and quality
gates are binding in this repo, and what wins when two documents disagree. This is
the **source of truth**: `CLAUDE.md` and the `.claude/rules/` files are
runtime guidance and reference implementation detail — where they conflict with this
document, this document wins.

**Not here.** The *procedural* half of the workflow (branch creation, PR discipline,
role hand-offs, the architect-review gate) is delegated to
[the agent process](SKILL.md) — see §Governance. How each gate is
implemented and configured, and which coverage gaps are consciously accepted, are
this project's own docs to author.

## Goal function

The goal function and *Scripts over instructions* are in
[`always-on.md`](always-on.md#goal-function).

## Core Principles

### I. Test-First (NON-NEGOTIABLE)

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

The implementer workflow enforces it from the issue's `## Test plan` section.
The test would have caught the prior behaviour. The converse — when a
*non-behavioural* regression still does not earn a guard test (a resource-only
cost, not correctness/safety) — is a target-project coverage decision to record
explicitly.

A test that pins a known production bug (`TestConfigValidationKnownGaps` style)
is allowed only when an issue tracks the fix; when fixed, the test MUST be
inverted to assert the correct behaviour.

**Rationale:** code-then-tests hides drift for months; writing the test first
makes the contract explicit and the divergence audible.

### II. Protocol Boundaries with Dependency Injection

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

Production wires real clients in `if __name__ == "__main__":` blocks; tests wire
doubles through the same constructor signature.

Each boundary is documented with the project's current boundary names in a
project-local runtime document. Implementations receive ready clients, never
credentials. Production entry points wire concrete clients, while the pipeline
and extraction helpers are called directly in tests.

**Rationale:** mocking internal logic lets production drift undetected; Protocol
doubles exercise the real code path with deterministic external state.

### III. Delivery Truthfulness

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

The ERROR names the missed items; the not-ok mark applies where the code has a
result type. A best-effort technical alert should be sent when the failure is
not the delivery channel itself.

A run that can tell which items were delivered records only those. Recording
before delivery is allowed only when a delivery failure is still an explicit
operational failure.

**Rationale:** users must be able to distinguish "there was nothing to
deliver" from "the system failed to deliver" — a silent green run that does
neither destroys trust.

### IV. Visibility Over Silence

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

This holds per field: an item that is usable but has an unusable field (an empty
URL, a missing image, a broken asset) is still emitted, with a gap marker. Fatal
input errors include no records and a malformed source.

The same holds for each later step: a failed transformation or technical alert
MUST NOT be collapsed into "nothing to report"; a failed delivery is §III.

An intentional broad catch that keeps the failure visible carries its reason
inline.

**Rationale:** silent degradation is the worst kind of bug — a visible gap or a
red CI badge is a forcing function for someone to look.

### V. Root Cause Before Fix

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

Instrumenting means inspecting logs, inputs, and the failure point before
proposing a change. When the behaviour to be designed is how an external system
is read or classified, repository reasoning alone is not evidence. The
observation names the failing record and an exact valid record from the same
captured response; a sibling feed, query or source does not stand in for it.
Compare candidate fix boundaries from broad to narrow: one that loses the valid
record needs an explicit product decision. Trace the current call path before
claiming that a narrow fix needs another fetch.

Reproduction is a step of planning: the `proposal` rule in `openspec/config.yaml`
says what the proposal records (the failing test, or the exact observation when
a test needs project-specific capture, and the root cause) before the design
exists. The core does not prescribe how evidence is captured; the target project
does. Captured bytes become a committed regression fixture only when a
production-behaviour test reads them in the same commit, and that test proves
preservation (the valid record still passes) rather than inferring it.

If the immediate fix proves too large for the current PR, the PR may ship a
**documented mitigation** (e.g. raise-and-skip, or a temporary unblock of an
unrelated CI failure, with a linked issue for the root cause), but the
mitigation itself must be a deliberate choice, not a guess.

**Rationale:** a shim that hides a root cause becomes load-bearing later;
cheap-now is expensive-later.

### VI. Fail-Fast Configuration

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

Load-time errors include missing required fields, out-of-range values such as
non-positive limits, references that do not resolve, mismatched schemas.

One load-time validation step is the gate.

**Rationale:** a config-validation gap otherwise surfaces at first use, far
from the edit that introduced it.

### VII. Simplicity First

The rule is stated in
[Operative principles](always-on.md#operative-principles); this section holds its detail.

No unrequested features, premature abstractions, or error-handling beyond what the task
needs (auth / payments / security excepted). Heuristic: if the solution could be half its
length, rewrite it; an abstraction with a single caller is inlined, not introduced.

Removing dead code is a separate, deliberate unit (one-PR-one-unit,
[the agent process](SKILL.md)), not silently widened scope. Prefer stdlib and
existing repo packages.

Mostly not machine-gated: "over-complicated" is a semantic judgement, enforced at
**plan stage** by the [architect review](SKILL.md#architect-review),
whose reviewer reads the [goal function](always-on.md#goal-function). The diff-stage
automated review blocks only two
narrow, worktree-verifiable triggers as a second pass: an added indirection with a
single call site and no stated reason, and duplicated logic whose finding
names an existing symbol and its repository-relative path. Every broader
simplicity opinion stays advisory at diff stage.

**Rationale:** over-engineering is a systematic LLM-agent failure mode, cheapest to
prevent as a standing default — more code is more bug/support surface (goal 1) and
more dev + runtime tokens (goal 2).

## Quality Gates

A PR MAY merge only when:

- The ruleset that `activate_protection` installs passes.
- The change has tests matching its behaviour (Principle I). New extraction
  logic gets an integration test against a saved fixture; new config rules
  get a unit test; new pipeline orchestration gets a Protocol-doubles test.
- A newly *rejected* coverage decision (a consciously-accepted gap, a scope-/cost-skip)
  is recorded in a coverage-gaps ledger (this project's own) so it isn't
  silently re-litigated — there is no auto-generated coverage inventory to update.
- Unresolved review threads the check passes (`P2`/`P3`, or another author's)
  are answered in PR comments before merge; the person merging holds this, no
  check does.
- For PRs that touch external extraction or API contracts, an E2E smoke test
  (real HTTP) has been run at least once on the branch.

## Governance

This document supersedes ad-hoc conventions in `CLAUDE.md` and `.claude/rules/`;
where they conflict, this document wins. They remain as runtime guidance and
implementation-detail references — kept short, kept linked, never the source
of truth on principles.

**Delegation of operational procedures.** This constitution retains the
**goal function** and the rules of §I–VII (held in [`always-on.md`](always-on.md)), the
**detail of §I–VII**,
the **Quality Gates**, and this **Governance** section as its canon. The *operational
procedural rules* are delegated to
[the agent process](SKILL.md). Delegation does **not** weaken their
authority: those rules bind equally; the skill, with `openspec/specs/`, is their
single source of truth (other mentions are links only). Amending them happens
in the skill and the specs; amending the *delegation itself* (what is canon vs. delegated) is
a Governance change made here.

Amendments are made via PR that modifies this file. Version policy:

- **MAJOR** — a principle is removed, redefined, or a procedural rule is
  reversed (e.g. Test-First downgraded to optional). Requires explicit human
  approval in the PR description.
- **MINOR** — a new principle or section is added, or a principle's scope
  is materially expanded.
- **PATCH** — clarifications, wording improvements, typo fixes, references
  updated, no semantic shift in rules.

Every PR description states which principles the change interacts with. The
reviewer (human + automated review) checks that the change does not violate
them; if it does, the violation MUST be recorded in the PR body with a
justification.
