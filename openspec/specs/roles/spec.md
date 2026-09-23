# roles Specification

## Purpose
Which roles the process has, which carrier fills each one in Claude Code and in Codex, and
how two agents share one procedure without duplication.

## Requirements

### Requirement: OpenSpec skills are the carriers of the procedure
The planner, implementer, and archive entry points SHALL remain the OpenSpec skills
(`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`), identical in Claude
Code and Codex, on the unmodified `spec-driven` schema. The portable proposal, specification,
design, task, architect-review, and delivery procedure SHALL live once in the shared
`agent-process` skill. `openspec/config.yaml` SHALL retain project context and point its
artifact rules to that skill rather than copy the procedure body. No forked schema, second
procedure copy, or second role-specific entry point SHALL exist.

#### Scenario: Procedure changes once
- **WHEN** a portable planning or delivery rule changes
- **THEN** one shared `agent-process` skill source changes and both agents follow it through their existing OpenSpec entry points without merging copied rule bodies

### Requirement: Roles and carriers
Roles SHALL be carried as follows: planner — `/opsx:propose` in Claude, `$openspec-propose`
in Codex; architect review — the `architect-reviewer` subagent in Claude (independent), a
self-review in Codex, both writing `architect-review.json` into the change directory as the last
step of the propose run, valid against `skills/agent-process/architect-review.schema.json`; implementer and fixer —
`openspec-apply-change` (`/opsx:apply`, `$openspec-apply-change`) executing `tasks.md`,
whose delivery tasks the `tasks` rule puts into every change; PR review — `claude-code-action` workflow and the Codex GitHub app;
merge — the person.

#### Scenario: Codex plans a change
- **WHEN** the person runs `$openspec-propose` in Codex
- **THEN** the change carries `architect-review.json` whose `reviewer` is `self-review` instead of `architect-reviewer`, valid against the review schema

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
