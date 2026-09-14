# state Specification

## Purpose
Where the process records which task is in which stage, and what moves it.

## Requirements

### Requirement: Project Status is the lifecycle field
The GitHub Project's built-in `Status` field SHALL be the lifecycle field; the process uses
only its built-in options and adds none.

#### Scenario: Linking an existing Project
- **WHEN** the process is linked to an existing Project
- **THEN** the Project's built-in `Status` options are required and preserved

### Requirement: Priority is set at creation
Priority SHALL be a Project field set when the issue is created; the planner asks the
person for it and sets it with `set_issue_priority`.

#### Scenario: Priority field drift
- **WHEN** the Project's priority field does not match the configured options
- **THEN** the mismatch is reported before any status is changed

### Requirement: Branch creation moves the issue to In Progress
Creating the `issue-N-<slug>` branch SHALL move the issue's Status to `In Progress`; a
board failure stops delivery visibly instead of leaving the branch without a status.

#### Scenario: Board failure
- **WHEN** the status move fails after the branch is created
- **THEN** the delivery stops with the error, not with a silent branch
