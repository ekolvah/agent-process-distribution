## Why

Tracking issue 9 asks whether [Ponytail](https://github.com/DietrichGebert/ponytail), an MIT
skill that pushes an agent to the smallest complete change, should join the process as an
optional skill for the planner, the reviewer, or both. The process already pushes against
bespoke code (`design.md` Context compares the rules), so the question is whether Ponytail adds
anything on top. Its benchmark is a hypothesis for this process, not evidence. The issue's
references are stale: `principles.md` is now `always-on.md`, and the `additions` rule was
removed (ADR 0027).

## Standard approach

Paired A/B with a no-skill baseline arm, same model and same tasks, runs interleaved. That is
the method of Ponytail's own agentic benchmark: "a headless Claude Code session per task, the
same agent with and without the skill … in one interleaved run"
(<https://github.com/DietrichGebert/ponytail/blob/main/benchmarks/README.md>). `design.md`
decision 1 names the departures and why `claude plugin eval` is not used.

## What Changes

- A paper gate first: an unresolvable conflict between Ponytail and §I–VII decides
  "not planned" without a pilot (design decision 4).
- Otherwise a pilot on two recently merged tasks: each one's delivery without Ponytail is
  arm A, and each is planned and delivered once more through `/opsx:propose` → `/opsx:apply`
  from A's base with Ponytail at a pinned release (decisions 1–3). The pilot stops after task
  1 when that task already decides.
- A new ADR records the comparison, the readings and the decision: an optional plugin (pinned
  version, install path, rollback) or not planned.
- On adoption only, `skills/agent-process/SKILL.md#install` gains one optional row. Nothing
  enforced changes, so no spec delta either way (`skip_specs`).
- No gate weakened: `start_change`, `ci_check`, `agent-review`, branch protection and human
  merge run unchanged for both arms.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None (`skip_specs`).

## Impact

- Added: `.agent-process/docs/adr/0046-ponytail-evaluation.md`.
- Edited on adoption only: `skills/agent-process/SKILL.md` (`## Install`).
- Pilot side effects, per task: a `pilot-base/<slug>` branch, a pilot issue and a pilot PR;
  one temporary ruleset on `pilot-base/**` with `main`'s approval and required checks; all
  closed or deleted after the readings; a session-only Ponytail load (design decision 2).
- Consumers: none until an adoption ships.
