## MODIFIED Requirements

### Requirement: Documents are guarded
In every tracked file, links SHALL resolve. An issue or PR reference SHALL appear only in a
history record: an ADR record under `.agent-process/docs/adr/`, `CHANGELOG.md`, or a change
under `openspec/changes/`. A document under `.claude/rules/`, and the skill's
`principles.md`, SHALL also state the question it answers.

#### Scenario: Narrative issue reference
- **WHEN** a comment, docstring or document outside the history records carries `#N`,
  `issue N`, `PR N` or `pull request N`, on one line or wrapped across two
- **THEN** CI reports the file

#### Scenario: History record keeps its references
- **WHEN** an ADR record, `CHANGELOG.md` or a change artifact carries an issue reference
- **THEN** CI does not report it
