## ADDED Requirements

### Requirement: ci_check lists its checks
`ci_check --list` SHALL print the names of its check registry as one JSON array, in run
order, and exit zero without running a check.

#### Scenario: List
- **WHEN** `ci_check --list` runs
- **THEN** stdout is a JSON array equal to the registry names in order, and no check command was started
