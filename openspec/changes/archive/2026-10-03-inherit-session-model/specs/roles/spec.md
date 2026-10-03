## ADDED Requirements

### Requirement: Plugin agents inherit the session model
Every plugin agent SHALL declare `model: inherit` and no `effort` in its frontmatter.

#### Scenario: Agent frontmatter read
- **WHEN** the frontmatter of a plugin agent is read
- **THEN** its `model` is `inherit` and it has no `effort` key
