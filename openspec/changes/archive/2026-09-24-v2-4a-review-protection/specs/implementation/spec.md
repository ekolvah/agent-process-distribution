## MODIFIED Requirements

### Requirement: ci_check is the one command every gate runs
One command, `ci_check`, SHALL be what the pre-push git hook and the CI workflow run; there
is no second list of checks.

#### Scenario: Push
- **WHEN** a branch is pushed
- **THEN** the pre-push hook runs `ci_check` as its only check, and CI runs the same command

## REMOVED Requirements

### Requirement: Stop hook names the next command
**Reason**: It gated only `issue-N-<slug>` branches, and no v2 delivery creates one: the
branch is named after its change, so the hook allowed every v2 turn. Its terminal state was
the review gate's stamp, and this change deletes the review gate.
**Migration**: `wait_for_pr.py` is the last Deliver task of every change, and the person is
the gate (ADR 0027 supersedes ADR 0021).
