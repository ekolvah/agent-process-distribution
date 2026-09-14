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
Every document SHALL state the question it answers, its links SHALL resolve, and an issue
reference SHALL be a pointer in parentheses, not narrative.

#### Scenario: Narrative issue reference
- **WHEN** a document mentions an issue as part of a sentence
- **THEN** CI reports it
