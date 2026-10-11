## ADDED Requirements

### Requirement: A simplify pass precedes the architect review
The architect-review procedure of the shared skill SHALL run `/simplify` on
`openspec/changes/<change>/` once per propose run, after `tasks.md` and before the first
architect review, and the plan's explanation SHALL state what `/simplify` changed.

#### Scenario: Plan written
- **WHEN** a propose run has written `tasks.md`
- **THEN** `/simplify` runs on the change directory before the `architect-reviewer` is invoked, and the explanation states what it changed
