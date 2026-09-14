## Purpose
Where the process records which task is in which stage, and what moves it.

## MODIFIED Requirements

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
