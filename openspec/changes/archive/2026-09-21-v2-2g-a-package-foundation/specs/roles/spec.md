## MODIFIED Requirements

### Requirement: OpenSpec skills are the carriers of the procedure
The planner, implementer, and archive entry points SHALL remain the OpenSpec skills
(`openspec-propose`, `openspec-apply-change`, `openspec-archive-change`), identical in Claude
Code and Codex, on the unmodified `spec-driven` schema. The portable proposal, specification,
design, task, architect-review, and delivery procedure SHALL live once in the shared
`agent-process` skill. `openspec/config.yaml` SHALL retain project context and point its
artifact rules to that skill rather than copy the procedure body. No forked schema, second
procedure copy, or second role-specific entry point SHALL exist.

#### Scenario: Procedure changes once
- **WHEN** a portable planning or delivery rule changes
- **THEN** one shared `agent-process` skill source changes and both agents follow it through their existing OpenSpec entry points without merging copied rule bodies
