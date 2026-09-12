# Goals

**Question this document answers:** what the agent process is for, what it optimizes, what
it deliberately does not do, and how we know v2 is better than v1.

Status: draft

## Requirements

- **GOAL-1** (MUST) The process serves one scenario: a person discusses a task with an
  agent → the agent plans → the person approves the plan → the agent implements and opens
  a PR → the person merges. Every gate is designed around those two human decisions.
- **GOAL-2** (MUST) Two agents are first-class carriers of every agent role: Claude Code
  and Codex. A role never depends on a capability only one of them has.
- **GOAL-3** (MUST) Target projects are GitHub repositories with Actions and a GitHub
  Project; stacks differ. Nothing in the core assumes a language or a test runner.
- **GOAL-4** (MUST) The only paid dependencies are the Claude and Codex subscriptions.
- **GOAL-5** (MUST) Priorities in strict order: (1) minimize future bug-fixing and support,
  (2) minimize token spend, (3) keep the process predictable and under user control.
- **GOAL-6** (SHOULD) v2 is accepted when: core scripts ≤ 1 000 lines and workflows
  ≤ 150 lines; a new project is installed with one plugin command plus `init` in ≤ 10
  minutes; an update needs no manual merge; the metrics in `70-telemetry.md` are no worse
  than v1 on the same task types.

## Rationale

v1 grew to 9 100 lines of scripts and 11 400 lines of tests for two root causes. First, the
process protected itself from agents with code at the exact points where a human already
decides (plan approval, merge): the automatic red-check on review, the orchestrator with
`max_runs` budgets, and the Stop gate duplicated the human gate. Second, Copier required a
mirror of the repository under `template/*.jinja` and tests to defend that mirror from
drift, so the delivery mechanism outgrew what it delivered. A third signal: project-specific
rules leaked into the shared core (`check_fixture_ratchet.py` guards HTML fixtures of one
parser project).

The goal function is the one in
[`principles.md`](../../.agent-process/docs/architecture/principles.md#goal-function); it is
not restated elsewhere.

## Non-goals

- An orchestrator that invokes models or routes evidence; the person is the orchestrator.
- Provider failover inside CI; a person opens another chat.
- Copier or any template mirror of the repository.
- A discovery role or fixture-capture machinery in the core.
- Codex hooks (until Codex stabilizes them).
- Per-label section sets for issues.
- Drift checks for branch protection; generated files carrying GitHub IDs.

## Open questions

- None at this level; area-level questions live in their own specs.

## Traceability

- Supersedes the framing of ADR 0011, 0015, 0019, 0021 once v2 lands
  (see `90-migration-v1-v2.md`).
- Spec-driven development adopted in the discussion of 2026-09-12 (#105).
