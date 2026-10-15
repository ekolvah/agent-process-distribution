## Why

The person deleted their global `~/.claude/CLAUDE.md` because it duplicated the goal function
of `principles.md`. That file was in every session; the plugin carries the goal function only
when the `agent-process` skill is read.

Observed on 2026-10-15 in this adopted repository: a propose session that never invoked the
`agent-process` skill held no goal function text. `CLAUDE.md` only links the skill's
Principles, and both session-start hooks (`plugin_env.py`, `skill_check.py`) print only failure
markers. `init` writes no instruction file to a consumer.

Platform behaviour (code.claude.com/docs):

- memory: `CLAUDE.md` and `.claude/rules/*.md` files are loaded at the start of every session;
  "Rules without a `paths` field are loaded unconditionally".
- context-window, What survives compaction: "Project-root CLAUDE.md and unscoped rules —
  Re-injected from disk".
- plugins-reference: "A `CLAUDE.md` at the plugin root isn't loaded as context … To include
  instructions that load into Claude's context, put them in a skill." A plugin therefore cannot
  ship always-on instructions; the repository's own instruction files are the standard carrier.

The global file also carried three rules the plugin lacks: brief answers by default; do not
redo a subagent's work; a standard, maintained tool over a script of our own, and on friction
look first for a wrong architectural choice.

## What Changes

- The `## Goal function` section of `principles.md` and the `## Claude harness` section of
  `SKILL.md` move, unchanged but for the rules below, into one file,
  `skills/agent-process/always-on.md`. Both documents link to it; `principles.md` Governance
  names it as part of the canon.
- `init` gains a step `rules` that writes the managed `.claude/rules/agent-process.md`: the
  managed marker line, then `always-on.md` of the installing release.
- This repository's `CLAUDE.md` imports `@skills/agent-process/always-on.md`.
- Rule 1: no edit (already in the harness). Rule 2: the harness subagent bullet. Rule 3:
  *Scripts over instructions*. See design D3.
- `SKILL.md#install` says what the rules file puts into each session.
- ADR 0043 records the carrier.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a new requirement, *An installed repository's sessions carry the goal
  function*; *The installed footprint is closed* gains the rules file; *This repository dogfoods
  its own process* gains the import.
- `roles`: *The skill carries the principles core and harness tactics* — the skill links
  `always-on.md` for the goal function and the harness instead of holding the harness.

## Impact

- Added: `skills/agent-process/always-on.md`,
  `.agent-process/docs/adr/0043-the-goal-function-reaches-every-session.md`.
- Edited: `skills/agent-process/scripts/init.py`, `skills/agent-process/SKILL.md`,
  `skills/agent-process/principles.md`, `agents/architect-reviewer.md`, `CLAUDE.md`,
  `.agent-process/docs/adr/0021-the-end-of-an-agent-turn-is-a-gated-event.md` (one link),
  `tests/publisher/init_harness.py`, `tests/publisher/test_init_config.py`,
  `tests/publisher/test_init_conflicts.py`, `tests/publisher/test_plugin.py`.
- Removed: none.
- Consumers: one new committed file, written by the next Install run; the release-drift check
  of `create_tracking_issue` and `start_change` already forces that run after each plugin
  release.
- Runtime cost: about 600 tokens in every session of an installed repository.
