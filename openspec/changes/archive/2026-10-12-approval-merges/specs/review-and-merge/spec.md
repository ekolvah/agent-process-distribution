## ADDED Requirements

### Requirement: The person's approval merges the agent's PR
Right after the agent creates its PR, the delivery SHALL run `enable_auto_merge <PR>`, which
SHALL enable auto-merge with the squash method only when the PR's `reviewDecision` is
`REVIEW_REQUIRED`. The explanation of the delivered change SHALL state the outcome.

#### Scenario: Approval required
- **WHEN** `enable_auto_merge` runs on a PR whose `reviewDecision` is `REVIEW_REQUIRED`
- **THEN** it runs `gh pr merge <PR> --auto --squash`, prints that the person's approval merges the PR, and exits 0

#### Scenario: No approval required
- **WHEN** `enable_auto_merge` runs on a PR whose `reviewDecision` is empty or `APPROVED`
- **THEN** it runs no merge command, prints that the person merges, and exits 1

#### Scenario: Auto-merge refused
- **WHEN** `gh pr merge --auto --squash` fails, as in a repository that does not allow auto-merge
- **THEN** `enable_auto_merge` prints gh's message and exits 2

#### Scenario: Approval merges
- **WHEN** the person approves the agent's PR on which `enable_auto_merge` exited 0
- **THEN** GitHub merges it with squash once its required checks pass, with no further action by the person
