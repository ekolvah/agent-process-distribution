## Context

After `goal-function-every-session` (issue 414) merges, `## Claude harness` lives in
`skills/agent-process/always-on.md` and its subagent bullet reads "Spawn a subagent only for
independent work, or for research that needs more than three round trips; do not redo the work
it reports." This change edits that bullet and the roles requirement as issue 414 leaves them.

## Goals / Non-Goals

**Goals:** an imperative delegation tactic, naming an agent type, whose trigger the session sees
before it reads.

**Non-Goals:** a hook, a counter of read calls, or a custom subagent definition.

## Decisions

### D1 — The bullet

The subagent bullet of `always-on.md` becomes:

> When a question takes two or more lookups (reads, searches, `gh`, web) of material you will
> not edit, ask the `Explore` subagent for the conclusion with `path:line` references. Spawn
> other subagents only for independent work; do not redo work a subagent reports.

- Observed on 2026-10-15: two `claude -p` runs (Claude Code 2.1.296) in local clones of this
  repository, asked which function computes the `compactions` column of `task-readings.csv`,
  where its input comes from and which tests cover it. With this bullet in an unscoped
  `.claude/rules/delegate.md` (session `a419d0f9-3fd9-4e0c-aef9-451e5e113680`), the main
  session's only tool call was `Agent` with `subagent_type` `Explore`: 48,479 tokens of main
  context at its last step, $0.58. Without it (session `0ff972b9-da96-4fa0-b6a9-0290d3e6e824`),
  two Grep and three Read calls: 60,279 tokens, $0.38. So the rule lifts the Agent tool's bar,
  and on one short question delegation costs more than it saves. The saving comes in long
  sessions, where every later turn re-reads the main context.
- Two or more is the threshold of the issue's 23% row. "More than three round trips" is known
  only after the third, when the reads are already in context.
- "Material you will not edit" is the issue's exploration definition: a file the session edits
  stays in the main context, where the edit needs it.

Alternatives:
- A `PreToolUse` hook that denies a second consecutive read: ruled out by the issue, and a
  denial spends a turn of its own.
- A custom read-only agent in `agents/`: `Explore` is the platform's own; a copy is a bespoke
  definition to maintain.
- A delegation step inside the propose and apply procedures, where most exploration happens:
  the observed spawns come from such steps, but exploration also happens outside them, and the
  propose investigation text is OpenSpec's vendored skill.

### D2 — Test

`test_skill_carries_principles_core_and_harness_tactics` in `tests/publisher/test_plugin.py`,
which issue 414 points at `always-on.md`, gains asserts that the harness contains
`` `Explore` ``, `two or more` and `path:line`. It fails on the issue-414 text.

### D3 — Measurement

The linked branch closes issue 424 on merge, so the Deliver group opens a measurement issue
(area `Token efficiency`) that carries this decision and the revert condition under Risks.
After ten changes merge following this one, compare `compactions` and `cost_usd` per PR in
`task-readings.csv` with the ten before, and count `Explore` calls per session in the
transcripts of both windows. Issue 414 merges inside the before window, so a fall in
compactions counts for this change only if `Explore` calls rose. Record the three numbers on
the measurement issue and close it.

## Risks / Trade-offs

- [`Explore` runs on the session's model and starts cold, so total spend can rise] → D3 reads
  `cost_usd`; if it rises with no fall in compactions, revert the bullet.
- [Issue 414 merges a roles requirement other than the text this delta copies] → task 0.2
  compares them and rewrites the delta on the merged text before RED.

## Migration Plan

Rollback: revert the PR.
