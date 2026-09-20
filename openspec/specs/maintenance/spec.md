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
In every tracked file, links SHALL resolve and an issue reference SHALL be a pointer in
parentheses, not narrative. A document under `.agent-process/docs/architecture/` or
`.claude/rules/` SHALL also state the question it answers.

#### Scenario: Narrative issue reference
- **WHEN** a document mentions an issue as part of a sentence
- **THEN** CI reports it

### Requirement: Native first
A process script SHALL exist only when GitHub, `gh`, OpenSpec, Claude Code or Codex are
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

### Requirement: A release tag matches the distributed version
The version in `.claude-plugin/plugin.json` and the marketplace entry SHALL match, and a
release SHALL use the tag `v<version>` on the default branch. The consumer caller and
Codex checkout SHALL pin that tag, and a change to distributed behavior SHALL bump the
version before release.

#### Scenario: Version drift
- **WHEN** the plugin manifest, marketplace entry, caller template, or release tag name different process versions
- **THEN** publisher validation fails before release
