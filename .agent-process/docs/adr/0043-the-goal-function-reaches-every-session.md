---
status: "accepted"
date: 2026-10-15
decision-makers: ekolvah
---

# The goal function reaches every session

## Context and Problem Statement

The goal function and the Claude harness tactics reached an agent only when it read the
`agent-process` skill. A session that never invoked it (a question, a settings change, a plugin
upgrade) worked without them; observed on 2026-10-15 in this repository. A plugin cannot ship
always-on instructions: a plugin-root `CLAUDE.md` is not loaded, and a skill body loads only
when invoked. The documented always-on carriers are the repository's `CLAUDE.md` and unscoped
`.claude/rules/*.md`, both re-injected from disk after compaction.

## Considered Options

* `init` copies one package file, `always-on.md`, into the managed `.claude/rules/agent-process.md`
* A plugin `SessionStart` hook prints the sections: a workaround for a missing native channel,
  invisible in `/context` Memory files, and it needs a heading parser
* An output style with `force-for-plugin`: overrides the person's own style and shapes replies
* `AGENTS.md`: the roles spec keeps instructions in `CLAUDE.md` and `.claude/rules/`
* `init` extracts the sections from `principles.md` and `SKILL.md`: a heading parser for text a
  moved file avoids
* The consumer's `CLAUDE.md` imports `principles.md` whole: about 3,400 tokens per session and
  an owned block in a consumer-owned file
* `additionalContext` from the skill check: its contract is silence when nothing needs action
* A managed-policy `CLAUDE.md`: needs administrator rights on each machine

## Decision Outcome

Chosen: **`init` copies `always-on.md` into the managed rules file**. The goal function, with
*Scripts over instructions*, and the Claude harness move from `principles.md` and `SKILL.md` into
`skills/agent-process/always-on.md`, which holds no relative link so its copy reads the same in
`.claude/rules/`. Both documents link it; `principles.md` Governance names it as the holder of
the canon's goal function. `init`'s `rules` step writes the managed marker line, a blank line
and the file; the release-drift exit of the delivery scripts forces Install after each release.
This repository, the publisher, imports the file from its `CLAUDE.md` instead of keeping a copy.

The three rules a person's global `CLAUDE.md` carried land as follows:

* Brief answers by default: no edit; the harness already says "Be concise by default".
* Do not redo a subagent's work: added to the harness subagent bullet.
* A standard, maintained tool over a script of our own, and on friction look first for the
  architectural cause: added to *Scripts over instructions*, a MINOR amendment of the goal
  function. Placed in §VII it would contradict that section.

### Consequences

* Good, because every session of an installed repository has the goal function and the harness
  from its first prompt and after compaction, as text the consumer has committed.
* Bad, because every installed session pays about 600 tokens; additions to `always-on.md` are
  runtime token spend (goal 2).
* Bad, because a session between a plugin update and the next Install reads the previous
  release's text.

### Confirmation

`tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file`, the `rules-unmanaged`
case of `tests/publisher/test_init_conflicts.py`, and
`tests/publisher/test_plugin.py::test_publisher_dogfoods_process`. Live: `/context` in a session
of an installed repository lists `.claude/rules/agent-process.md` under Memory files.

### Deletion condition

Remove the `rules` step and the consumer's file once Claude Code loads a plugin's instructions
into every session natively.
