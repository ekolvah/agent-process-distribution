# Planning

**Question this document answers:** how the process gets high-quality plans out of agents,
and what the person approves before implementation starts.

Status: draft

## Requirements

- **PLAN-1** (MUST) Substantive work starts from a GitHub issue created through an issue
  form that carries the plan structure: Context, Acceptance criteria, Test plan,
  Implementation outline, Docs to update, Out of scope, Architect review, Agent handoff.
- **PLAN-2** (MUST) The `plan-issue` skill reads the code and the prior art before writing
  a plan, and asks the person instead of guessing when a decision is theirs.
- **PLAN-3** (MUST) A non-trivial plan gets an architect review before implementation: the
  `architect-reviewer` subagent in Claude (independent), a self-review section in Codex.
  Criteria are `principles.md` §I–VII; findings are recorded in `## Architect review`.
- **PLAN-4** (MUST) The person approves the plan; that approval is the gate. The
  validator checks only that the headings exist and `## Agent handoff` is filled.
- **PLAN-5** (MUST) The issue references the system-spec requirement IDs it implements;
  a PR that changes target behaviour updates the spec in the same PR.
- **PLAN-6** (SHOULD) Bugs ship a reproducing test before the fix (`40-implementation.md`,
  IMPL-1); the core does not prescribe how evidence is captured.
- **PLAN-7** (MUST NOT) No per-label section sets; no `discovery` role or fixture-capture
  script in the core; agents do not change issue labels.
