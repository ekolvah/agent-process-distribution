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
Priority SHALL be a Project field set together with the first status of the tracking issue,
in one call (`set_status <N> "<Status>" --priority <name>`), fields and options resolved by
name; a Project the script cannot choose SHALL be reported, not guessed. The delivery task
that creates the issue SHALL ask the person for the priority; no later delivery task asks.

#### Scenario: Tracking issue created
- **WHEN** the implementing run sets the first status of a new tracking issue with a priority
- **THEN** both fields are set in one call and the issue is an item of the repository's Project

#### Scenario: Priority asked once
- **WHEN** the implementing run creates the tracking issue
- **THEN** it asks the person for the priority before the first status and never again

#### Scenario: Priority field drift
- **WHEN** the Project has no option for the given priority
- **THEN** the run reports it before any status is changed

### Requirement: Branch creation moves the issue to In Progress
Creating the `issue-N-<slug>` branch SHALL move the issue's Status to `In Progress`; a
board failure stops delivery visibly instead of leaving the branch without a status.

#### Scenario: Board failure
- **WHEN** the status move fails after the branch is created
- **THEN** the delivery stops with the error, not with a silent branch
