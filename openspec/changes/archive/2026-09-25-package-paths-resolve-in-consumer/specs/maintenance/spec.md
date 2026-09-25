## MODIFIED Requirements

### Requirement: Documents are guarded
In every tracked file, links SHALL resolve and an issue reference SHALL be a pointer in
parentheses, not narrative. A document under `.claude/rules/`, and the skill's
`principles.md`, SHALL also state the question it answers.

#### Scenario: Narrative issue reference
- **WHEN** a document mentions an issue as part of a sentence
- **THEN** CI reports it
