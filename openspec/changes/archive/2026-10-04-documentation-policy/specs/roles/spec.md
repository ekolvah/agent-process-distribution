## ADDED Requirements

### Requirement: The skill carries the documentation policy
The `agent-process` skill SHALL state where an agent writes repository knowledge — `CLAUDE.md`,
`.claude/rules/` with `paths:`, ADRs, auto-memory — and that each fact has one home.

#### Scenario: A consumer reads the documentation policy from the skill
- **WHEN** a consumer session invokes the `agent-process` skill
- **THEN** the skill body names `CLAUDE.md`, `.claude/rules/` with `paths:`, ADRs, auto-memory and the one-home rule
