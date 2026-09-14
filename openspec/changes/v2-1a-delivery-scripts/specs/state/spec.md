## Purpose
Where the process records which task is in which stage, and what moves it.

## MODIFIED Requirements

### Requirement: Priority is set at creation
Priority SHALL be a Project field set together with the first status of the tracking issue,
in one call (`set_status <N> "<Status>" --priority <name>`), fields and options resolved by
name; a Project the script cannot choose SHALL be reported, not guessed.

#### Scenario: Tracking issue created
- **WHEN** the implementing run sets the first status of a new tracking issue with a priority
- **THEN** both fields are set in one call and the issue is an item of the repository's Project

#### Scenario: Priority field drift
- **WHEN** the Project has no option for the given priority
- **THEN** the run reports it before any status is changed
