## ADDED Requirements

### Requirement: ci_check limits code complexity
`ci_check` SHALL fail when a function exceeds the configured complexity limits or a Python
module exceeds the configured size limit. A complexity suppression that no longer suppresses
anything SHALL fail.

#### Scenario: Function over the complexity limit
- **WHEN** a Python function in a linted scope exceeds the complexity limit without a suppression
- **THEN** `ci_check` exits non-zero and names the function and the rule

#### Scenario: Module over the size limit
- **WHEN** a Python module in a checked scope exceeds the size limit
- **THEN** `ci_check` exits non-zero and names the module

#### Scenario: Stale baseline entry
- **WHEN** a complexity suppression remains on a function that no longer exceeds the limit
- **THEN** `ci_check` exits non-zero and names the unused suppression
