## ADDED Requirements

### Requirement: A collection failure names the way to RED
When a `check_red` run does not complete, `check_red` SHALL still exit 2 without a verdict,
and its stderr SHALL name the way to a judgeable RED for a test module that failed at
collection because its import target does not exist yet: a stub of the target whose body
raises `NotImplementedError`, so the test fails in its body.

#### Scenario: Test of code that does not exist yet
- **WHEN** `check_red` runs node ids of a test module whose import target does not exist
- **THEN** it exits 2, and its stderr names the module that failed at collection and the `NotImplementedError` stub
