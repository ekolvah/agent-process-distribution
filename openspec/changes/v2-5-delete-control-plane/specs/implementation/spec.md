## ADDED Requirements

### Requirement: No budgets and no Codex-side hooks
The core SHALL NOT have budgets (`max_runs`) for agent runs and SHALL NOT have Codex-side
hooks.

#### Scenario: Looping agent
- **WHEN** an agent loops on a PR
- **THEN** it is visible on the PR, not stopped by a counter
