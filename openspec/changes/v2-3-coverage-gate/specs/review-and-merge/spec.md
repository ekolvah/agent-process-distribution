## ADDED Requirements

### Requirement: Every scenario is covered before merge
A PR SHALL be mergeable only when every scenario of its change's spec delta is covered by a
test that ran green in the PR's checks (read from the JUnit report the consumer's test-runner
command writes at the path `AGENTS.md` declares), or is marked `n/a: <reason>` in the `tasks.md` the
person approved. An uncovered scenario SHALL be a failed check, not a review comment.

#### Scenario: Missing test
- **WHEN** a scenario has no test in the PR and no `n/a` in `tasks.md`
- **THEN** a required check fails and names the scenario
