## MODIFIED Requirements

### Requirement: Branch creation moves the issue to In Progress
Creating the linked branch of a change's tracking issue (`start_change <change>`) SHALL move
the issue's Status to `In Progress`; a board failure stops delivery visibly instead of leaving
the branch without a status.

#### Scenario: Board failure
- **WHEN** the status move fails after the branch is created
- **THEN** the delivery stops with a non-zero exit whose message names the steps left, not with a silent branch
