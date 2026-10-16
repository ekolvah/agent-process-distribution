## MODIFIED Requirements

### Requirement: Reviewer instructions name the simplicity triggers
The review contract SHALL be one file the Claude review job reads from the trusted checkout,
and SHALL name reinvented functionality and unnecessary complexity as findings and the two
narrow simplicity triggers.

#### Scenario: Contract and principles
- **WHEN** the review contract is read
- **THEN** it names the indirection and the duplication trigger

### Requirement: The review contract labels each principle
The review contract SHALL name the trusted checkout's `always-on.md`
(`trusted/skills/agent-process/always-on.md`, which states the rules of §I–VII) as review
policy and SHALL label a diff's breach of each of §I–VI `P0` or `P1`.

#### Scenario: Each principle has a severity
- **WHEN** the review contract is read
- **THEN** its policy source names `trusted/skills/agent-process/always-on.md` and no `principles.md`, and its `P0`/`P1` class names a breach of each of §I–VI
