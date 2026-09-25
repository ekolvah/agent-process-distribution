## ADDED Requirements

### Requirement: No local hook reads protection
No local hook SHALL read the installed branch protection or rulesets: a push is gated by
`ci_check` alone, and a merge by the ruleset that protection activation writes.

#### Scenario: Push reads no protection
- **WHEN** a branch is pushed through the pre-push hook
- **THEN** the hook runs `ci_check` and issues no read of branch protection or rulesets

## REMOVED Requirements

### Requirement: Required checks protect the default branch
**Reason**: Its two lists, the drift probe in the pre-push hook and the review gate that
judged both lists are v1 mechanisms: classic protection written by
`install_branch_protection`, checked by `check_branch_protection`, and judged by
`review_gate`. This change deletes all three.
**Migration**: `No local hook reads protection`, and distribution's `Protection activation
observes quality first`, which writes both contexts into the ruleset. The person deletes
classic protection. `wait_for_pr` names a failed context on the head.
