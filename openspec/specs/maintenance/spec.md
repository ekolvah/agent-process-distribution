# maintenance Specification

## Purpose
How the process records its decisions and keeps its documents readable.

## Requirements

### Requirement: Decisions are MADR records
Every architectural decision SHALL be a MADR record under `.agent-process/docs/adr/` with the required
sections and a known status; records are immutable after acceptance.

#### Scenario: ADR status
- **WHEN** an ADR carries an unknown status or lacks a required section
- **THEN** CI reports it

### Requirement: Documents are guarded
In every tracked file, links SHALL resolve. An issue or PR reference SHALL appear only in a
history record: an ADR record under `.agent-process/docs/adr/`, `CHANGELOG.md`, or a change
under `openspec/changes/`. A document under `.claude/rules/`, and the skill's
`principles.md`, SHALL also state the question it answers.

#### Scenario: Narrative issue reference
- **WHEN** a comment, docstring or document outside the history records carries `#N`,
  `issue N`, `PR N` or `pull request N`, on one line or wrapped across two
- **THEN** CI reports the file

#### Scenario: History record keeps its references
- **WHEN** an ADR record, `CHANGELOG.md` or a change artifact carries an issue reference
- **THEN** CI does not report it

### Requirement: Native first
A process script SHALL exist only when GitHub, `gh`, OpenSpec or Claude Code are
shown not to do the job. The ADR for any core addition SHALL carry a section "Native
alternatives considered".

#### Scenario: New script proposed
- **WHEN** a PR adds a core script
- **THEN** its ADR names the native alternatives and why they fall short

### Requirement: Every core ADR states its deletion condition
Every ADR that adds to the core SHALL state what would be deleted if the addition stopped
paying for itself.

#### Scenario: ADR review
- **WHEN** an ADR adding to the core is reviewed
- **THEN** its deletion condition is present
