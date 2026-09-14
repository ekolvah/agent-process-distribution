## ADDED Requirements

### Requirement: Cycle time contains no human step
From `In progress` to a mergeable PR (checks green, threads resolved) there SHALL be no
human step: reviews start on PR open, the implementing run applies findings, the person is
asked only to merge. Cycle time SHALL be measured per PR.

#### Scenario: PR opened
- **WHEN** the implementing run opens the PR
- **THEN** checks and reviews start without a trigger comment
