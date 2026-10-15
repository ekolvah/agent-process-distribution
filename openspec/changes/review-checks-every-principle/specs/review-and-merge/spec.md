## ADDED Requirements

### Requirement: The review contract labels each principle
The review contract SHALL name the trusted checkout's `principles.md` (`trusted/skills/agent-process/principles.md`)
as review policy and SHALL label a diff's breach of each of §I–VI `P0` or `P1`.

#### Scenario: Each principle has a severity
- **WHEN** the review contract is read
- **THEN** its policy source names `trusted/skills/agent-process/principles.md` and its `P0`/`P1` class names a breach of each of §I–VI
