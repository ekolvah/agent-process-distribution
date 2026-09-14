## Purpose
Where the process records which task is in which stage, and what moves it.

## MODIFIED Requirements

### Requirement: Priority is set at creation
Priority SHALL be a Project field set when the tracking issue is created; the delivery task
that creates the issue SHALL ask the person for it.

#### Scenario: Tracking issue created
- **WHEN** the implementing run creates the tracking issue
- **THEN** it asks the person for the priority and sets the field

#### Scenario: Priority field drift
- **WHEN** the Project has no option for the given priority
- **THEN** the run reports it before any status is changed
