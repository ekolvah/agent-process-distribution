## ADDED Requirements

### Requirement: Every archived requirement is covered by a test
Every requirement in `openspec/specs/` SHALL be covered by at least one test in this
repository that names its title; a requirement without a test SHALL fail CI. Consumer
conformance is the consumer's own `ci_check`; there SHALL be no publisher/consumer test
split and no rendered-template tests.

#### Scenario: Test deleted
- **WHEN** the last test naming a requirement is deleted
- **THEN** CI fails on the next push
