## Purpose
How the process stays small while agents extend it, and how future support of the process
itself is kept low.

## ADDED Requirements

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
