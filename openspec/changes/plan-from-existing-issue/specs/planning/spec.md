## ADDED Requirements

### Requirement: A change planned from an issue is tracked by it
When a change is planned from an existing issue, the planner SHALL write that issue's number
into the `tracking issue <N>` token of Group 0 as it writes `tasks.md`.

#### Scenario: Plan from an existing issue
- **WHEN** a change is planned from an existing issue
- **THEN** Group 0 of its `tasks.md` carries that issue's number, and `create_tracking_issue` creates no issue and moves that issue to `Planned`
