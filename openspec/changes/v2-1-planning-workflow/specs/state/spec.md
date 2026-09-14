## Purpose
Where the process records which task is in which stage, and what moves it.

## ADDED Requirements

### Requirement: Priority is set at creation
Priority SHALL be a Project field set when the tracking issue is created; the skill that
creates the issue SHALL ask the person for it.

#### Scenario: Tracking issue created
- **WHEN** `implement-change` creates the tracking issue
- **THEN** it asks the person for the priority and sets the field
