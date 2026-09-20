## ADDED Requirements

### Requirement: The ruleset blocks unsafe default-branch updates
The installed repository ruleset SHALL require a pull request, block deletion, and block
non-fast-forward updates for the default branch. It SHALL have no process bypass actor.

#### Scenario: Direct default-branch update
- **WHEN** an actor without an external administrative bypass tries to update the default branch outside a qualifying pull request
- **THEN** GitHub rejects the update under the installed ruleset

### Requirement: Official review apps are advisory
The thin caller SHALL invoke `anthropics/claude-code-action@v1` directly for PR review, and
`init` SHALL print the instruction for the person to enable Codex automatic reviews. The
process SHALL NOT install a reusable review workflow, request Codex by comment, parse either
reviewer's output, or make a review result a required status check. Review comments and
threads SHALL remain visible for the agent and person to address; the person decides
whether the PR may merge.

#### Scenario: Pull request review
- **WHEN** a pull request opens or its head changes after installation is complete
- **THEN** the caller starts the Claude action and the person's Codex app setting independently requests the official reviews without a process parser or fallback

#### Scenario: Review unavailable
- **WHEN** either review app is unavailable or fails to publish
- **THEN** the absence or failed review job stays visible and does not masquerade as a clean process verdict

## MODIFIED Requirements

### Requirement: Required checks protect the default branch
The installed repository ruleset SHALL require the head-bound `quality / quality` context
from the pinned reusable workflow and require branches to be current before merging. The
required context SHALL be bound by name and the GitHub Actions integration, not by a
consumer-editable assertion that authenticates the caller file. The person SHALL inspect
every `.github/workflows/**` diff on the current PR head before merge; repositories that
can use organization-level required workflows MAY add that stronger external trust anchor.

#### Scenario: Missing required context
- **WHEN** the PR head has no successful `quality / quality` context
- **THEN** the ruleset blocks the merge

## REMOVED Requirements

### Requirement: Local safety on both carriers
**Reason**: the distributed plugin ships no hooks or deny-list; the repository ruleset is
the portable guard, while this publisher's local settings remain repository-specific.
**Migration**: use the installed ruleset and preserve person-only merge as an explicit
delivery boundary.

### Requirement: Codex reviews on the author's request, Claude is the fallback
**Reason**: installation now uses the two official review integrations directly and makes
their reviews advisory; there is no process-owned request/wait/fallback workflow.
**Migration**: enable Codex automatic review from the printed instruction and keep the
Claude action job in the one caller.

### Requirement: Reviewer instructions name the simplicity triggers
**Reason**: the process no longer distributes or enforces one bespoke review contract for
the two official apps.
**Migration**: repository instructions and the apps' native review behavior remain visible
inputs to the person's review.

### Requirement: Unresolved P0/P1 threads fail the review check
**Reason**: review is advisory and the bespoke required review check is removed.
**Migration**: agents answer or resolve findings they address, and the person decides
whether unresolved conversation blocks merge.
