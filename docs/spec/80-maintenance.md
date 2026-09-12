# Maintenance

**Question this document answers:** how the process stays small while agents extend it,
and how future support of the process itself is kept low.

Status: draft

## Requirements

- **MAINT-1** (MUST) **Native first.** A process script exists only when it is shown that
  GitHub, `gh`, Claude Code or Codex do not already do the job. The ADR for any core
  addition carries a section "Native alternatives considered".
- **MAINT-2** (MUST) **A script is justified by an observed, repeated failure**, never a
  hypothetical one. A single failure is fixed by a line in the skill; the second
  occurrence earns the script.
- **MAINT-3** (MUST) Core scripts are stack-agnostic: `gh`, `git` and the standard
  library only. Anything stack-specific is the consumer's `AGENTS.md` or `ci_check`.
- **MAINT-4** (MUST) Tests in this repository cover the scripts (unit) and the spec
  format; consumer conformance is the consumer's own `ci_check`. No publisher/consumer
  test split, no rendered-template tests.
- **MAINT-5** (MUST) Versioning: plugin version and git tag `vN`; reusable workflows are
  pinned by tag in consumers; a breaking change is a major tag with a migration note.
- **MAINT-6** (MUST) Every ADR that adds to the core states what would be deleted if the
  addition stopped paying for itself; the spec's `## Non-goals` is the running list.
- **MAINT-7** (MUST) Size budget: core scripts ≤ 1 000 lines, workflows ≤ 150 lines
  (GOAL-6). Exceeding it is a finding, not a default.
- **MAINT-8** (SHOULD) Deterministic rules live in scripts with exit codes, prohibitions in
  deny-lists or hooks, never in prose the agent has to remember
  (`principles.md`, "scripts over instructions").

## Rationale

The v1 inventory shows where lines come from when MAINT-1/2 are absent: `open_pr.py` from
one unclosed issue, `check_fixture_ratchet.py` from one project's parser tests, a review
state machine from one quota outage (ADR 0003). Each was a reasonable local fix; the sum
was a process larger than the projects it served. The self-hosting mirror (ADR 0013)
doubled the cost of every change: each script edited twice, each rendered again in tests.

MAINT-4 removes the largest single test cost: `tests/publisher/` (render, drift, adoption,
bootstrap — about 5 000 lines) tested the delivery mechanism, which `10-distribution.md`
no longer has.

## Non-goals

- A self-applied template of this repository.
- Backward compatibility of internal script APIs; only the skill's user-facing commands
  and the reusable workflow inputs are contracts.

## Open questions

- Whether the size budget is enforced by a test or reviewed by hand; settled after the
  first three v2 PRs show whether it is ever approached.

## Traceability

- ADR 0013 (template self-hosting) — superseded once v2 lands.
- ADR 0017 (publisher tests stay in source) — superseded by MAINT-4.
- `principles.md` §VII (Simplicity First) — the principle MAINT-1/2 operationalize.
