## ADDED Requirements

### Requirement: Size budget
A workflow under `.github/workflows/` SHALL stay within 150 lines.

#### Scenario: Workflow over the budget
- **WHEN** a workflow under `.github/workflows/` exceeds 150 lines
- **THEN** the test suite fails and names the workflow
