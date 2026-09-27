# roles Specification

## Purpose
Which roles the process has and which Claude Code entry point carries each one.

## Requirements

### Requirement: OpenSpec skills are the carriers of the procedure
The planner, implementer, and archive entry points SHALL remain the OpenSpec skills
(`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`) in Claude Code, on
the unmodified `spec-driven` schema. The portable proposal, specification, design, task,
architect-review, and delivery procedure SHALL live once in the shared `agent-process` skill.
`openspec/config.yaml` SHALL retain project context and point its artifact rules to that
skill rather than copy the procedure body. No forked schema, second procedure copy, or
second role-specific entry point SHALL exist.

#### Scenario: Procedure changes once
- **WHEN** a portable planning or delivery rule changes
- **THEN** one shared `agent-process` skill source changes and Claude Code follows it through its OpenSpec entry points without merging copied rule bodies

### Requirement: Provenance is one line in the tracking issue
"Who planned, who implemented" SHALL be one line in the tracking issue, not a catalogue file.

#### Scenario: Reading provenance
- **WHEN** a person opens the issue
- **THEN** the planner and implementer carriers are visible without opening any other file

### Requirement: Claude Code carries every role
Claude Code SHALL be the only carrier of every agent role: planner — `/opsx:propose`;
architect review — the `architect-reviewer` subagent, writing `architect-review.json` into
the change directory as the last step of the propose run, valid against
`skills/agent-process/architect-review.schema.json`; implementer and fixer —
`openspec-apply-change` (`/opsx:apply`) executing `tasks.md`, whose delivery tasks the `tasks`
rule puts into every change; PR review — the `claude-code-action` workflow; merge — the
person.

#### Scenario: Another carrier named
- **WHEN** `start_change` is given a planner or implementer other than `Claude`, or an architect review names a reviewer other than `architect-reviewer`
- **THEN** the argument or the review is rejected before any branch exists
