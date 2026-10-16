## Why

Exploration reads fill the main context and drive compactions. Issue 424 records the
measurement (2026-10-01..15): runs of two or more consecutive exploration steps, less a
2k-token summary, are 23% of context growth, an upper bound of roughly 4–6 of 25 compactions.

The harness tactic "Spawn a subagent only for independent work, or for research that needs
more than three round trips" is not followed. Observed in the local transcripts of this
repository modified 2026-10-01..15 (71 files): the tactic's text appears in 10. No session
spawned a subagent for exploration. Every subagent spawned after the text appeared was an
imperative step of a procedure: the architect reviewer of `/opsx:propose` or the four review
agents of `/simplify`. Two causes:

- The text is absent from most sessions. `goal-function-every-session` (issue 414) loads the
  harness into every session.
- Where present, it is a limit ("only"), not an instruction, and names no agent type. The Agent
  tool description Claude Code gave the session that planned this change (2026-10-15) reads:
  "**Do not spawn agents unless the user asks.** … Only use this tool when the user explicitly
  says to use a subagent, or names one of the available agent types."

Platform (code.claude.com/docs/en/sub-agents, Explore): "A fast, read-only agent optimized
for searching and analyzing codebases"; "This keeps exploration results out of your main
conversation context."; "**Model**: the main conversation's model."

## What Changes

- The harness subagent bullet becomes an imperative that names `Explore` (design D1).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `roles`: *The skill carries the principles core and harness tactics* gains the delegation
  tactic.

## Impact

- Edited: `skills/agent-process/always-on.md` (one bullet), `tests/publisher/test_plugin.py`
  (one test extended).
- No ADR: the decision is one reversible line of tactic, recorded in `design.md`.
