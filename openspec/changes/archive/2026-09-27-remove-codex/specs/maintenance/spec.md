## MODIFIED Requirements

### Requirement: Native first
A process script SHALL exist only when GitHub, `gh`, OpenSpec or Claude Code are
shown not to do the job. The ADR for any core addition SHALL carry a section "Native
alternatives considered".

#### Scenario: New script proposed
- **WHEN** a PR adds a core script
- **THEN** its ADR names the native alternatives and why they fall short
