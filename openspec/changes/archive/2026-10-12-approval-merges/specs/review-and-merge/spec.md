## ADDED Requirements

### Requirement: The person's approval merges the agent's PR
Right after the agent creates its PR, the delivery SHALL run `gh pr merge <PR> --auto --squash`.
The approval ruleset SHALL be what holds the PR for the person; the delivery SHALL add no check
of its own before enabling auto-merge. Install SHALL have the person allow auto-merge on the
repository with `gh repo edit --enable-auto-merge`.

#### Scenario: Auto-merge after the PR
- **WHEN** the agent follows the skill's Delivery procedure
- **THEN** it runs `gh pr merge <PR> --auto --squash` after `gh pr create` and before `agent-process wait_for_pr`

#### Scenario: Approval merges
- **WHEN** the person approves the agent's PR on which auto-merge is enabled
- **THEN** GitHub merges it with squash once its required checks pass, with no further action by the person
