## REMOVED Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
**Reason**: The v1 caller `ci.yml`, which reported `quality / quality` from the trusted driver, is deleted, so each PR runs quality once.
**Migration**: `A context the PR cannot change gates every head` names `agent-review / agent-review` as the same-head catcher beside `agent-process / quality`.

## ADDED Requirements

### Requirement: A context the PR cannot change gates every head
Every head of this repository SHALL be gated by a required context that the PR cannot
change: `agent-review / agent-review`, which reviews that head. A required context that runs
the PR's own driver, `agent-process / quality`, SHALL be required only beside it. Each PR
SHALL run the quality driver once.

#### Scenario: PR weakens its own driver
- **WHEN** a PR of this repository changes the driver that `agent-process / quality` runs
- **THEN** the contexts the repository declares required for that head still include `agent-review / agent-review`

#### Scenario: Quality runs once per PR
- **WHEN** a PR of this repository opens or receives a push
- **THEN** `agent-process / quality` is the only check run that executes the quality driver on its head
