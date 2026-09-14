# roles Specification

## Purpose
Which roles the process has, which carrier fills each one in Claude Code and in Codex, and
how two agents share one procedure without duplication.

## Requirements

### Requirement: OpenSpec skills are the carriers of the procedure
The planner, implementer and archive procedures SHALL be the OpenSpec skills
(`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`), identical in Claude
Code and Codex. The process SHALL extend them only through `openspec/config.yaml` rules, the
forked schema; no second copy of the steps and no second entry point SHALL exist.

#### Scenario: Procedure changes once
- **WHEN** a planning rule changes
- **THEN** exactly one file changes (`config.yaml` or the schema) and both agents follow it

### Requirement: Roles and carriers
Roles SHALL be carried as follows: planner — `/opsx:propose` in Claude, `$openspec-propose`
in Codex; architect review — the `architect-reviewer` subagent in Claude (independent), a
self-review in Codex, both writing the `architect-review` artifact; implementer and fixer —
`openspec-apply-change` (`/opsx:apply`, `$openspec-apply-change`) executing `tasks.md`,
whose delivery tasks the `tasks` rule puts into every change; PR review — `claude-code-action` workflow and the Codex GitHub app;
merge — the person.

#### Scenario: Codex plans a change
- **WHEN** the person runs `$openspec-propose` in Codex
- **THEN** the change carries a self-review `architect-review` artifact instead of a subagent review

### Requirement: Provenance is one line in the tracking issue
"Who planned, who implemented" SHALL be one line in the tracking issue, not a catalogue file.

#### Scenario: Reading provenance
- **WHEN** a person opens the issue
- **THEN** the planner and implementer carriers are visible without opening any other file

### Requirement: Route selection is the person's
Which agent runs a role SHALL be decided by which chat the person opens. No file SHALL record
a "default adapter".

#### Scenario: Switching agents
- **WHEN** the person opens the other agent for the next role
- **THEN** no configuration changes
