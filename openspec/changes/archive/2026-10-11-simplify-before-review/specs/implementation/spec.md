## ADDED Requirements

### Requirement: A simplify pass opens Verify
The `tasks` procedure of the shared skill SHALL open Verify with `/simplify` without an
argument, its edits committed, before `openspec validate` and the quality `test`.

#### Scenario: Implementation done
- **WHEN** the implementation groups of a change are committed
- **THEN** Verify runs `/simplify` without an argument first, then `openspec validate` and the quality `test`
