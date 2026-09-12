# Goals

**Question this document answers:** what the agent process is for, what it optimizes, and
how we know v2 is better than v1.

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
  (2) minimize token spend, (3) keep the process predictable and under user control
  ([`principles.md`](../../.agent-process/docs/architecture/principles.md#goal-function)).
- **GOAL-6** (SHOULD) v2 is accepted when: core scripts ≤ 1 000 lines and workflows
  ≤ 150 lines; a new project is installed with one plugin command plus `init` in ≤ 10
  minutes; an update needs no manual merge; the metrics in `70-telemetry.md` are no worse
  than v1 on the same task types.
- **GOAL-7** (MUST NOT) The core contains no orchestrator that invokes models or routes
  evidence, no provider failover inside CI, and no template mirror of the repository; the
  person is the orchestrator.
