## ADDED Requirements

### Requirement: The skill check passes the seeded format
The skill check `.claude/agent-process-check.py` that a run installs SHALL be left unchanged by
the seeded `ruff-format` hook whatever the consumer's ruff configuration.

#### Scenario: Any consumer ruff configuration
- **WHEN** the seeded `ruff-format` hook runs at the seeded pin on the installed skill check, with no ruff configuration or with another `line-length`
- **THEN** it passes and the file is unchanged
