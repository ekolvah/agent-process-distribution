## Why

v1 grew to 9 100 lines of scripts and 11 400 lines of tests by protecting the process from
agents with code at the exact points where a person already decides (plan approval, merge),
and by delivering itself through a Copier mirror that needed its own drift tests. v2 rebuilds
the process around the two human decisions and on industry standards instead of bespoke code.

## What Changes

- One scenario: a person discusses a task with an agent → the agent plans → the person
  approves → the agent implements and opens a PR → the person merges.
- Two agents, Claude Code and Codex, carry every agent role; a role never depends on a
  capability only one of them has.
- Targets: GitHub repositories with Actions and a GitHub Project, mixed stacks; no language
  or test-runner assumption in the core; the only paid dependencies are the two subscriptions.
- Priorities in strict order: (1) minimize future bug-fixing and support, (2) minimize token
  spend, (3) keep the process predictable and under user control.
- Standards replace bespoke code: OpenSpec (specs, planning, apply, archive), Agent Skills,
  Claude Code plugin + Codex skills + reusable workflows (delivery), GitHub Rulesets and
  Projects (gates and state), hooks and deny-lists (guardrails), OpenTelemetry (measurement).
- **BREAKING**: the control plane, Copier mirror, review state machine and branch-protection
  scripts are removed by the changes v2-1 … v2-6 (tracking issue #107).
- Acceptance of v2 as a whole: the size budget of `maintenance` holds; a new project is
  installed in ≤ 10 minutes; an update never needs a three-way merge of process files; the
  `telemetry` metrics are no worse than v1 on the same task types.

This change writes the ADR that records all of the above and the two rules every later
core addition follows.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `maintenance` (baseline from #109): adds the two ADR rules — native first, deletion
  condition; the size budget arrives with `v2-5-delete-control-plane`.

## Impact

- New ADR "v2" in `.agent-process/docs/adr/`, with the OpenSpec vs Spec Kit trade study as
  Considered options; ADR 0011, 0013, 0015, 0019, 0021, 0022, 0023 marked superseded.
- No code changes.
