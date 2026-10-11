## ADDED Requirements

### Requirement: The review policy is what the session loads from the base
The review contract and the review job's prompt SHALL name as the review policy the contract
itself and the root `CLAUDE.md` and root `.claude/rules/` of the PR worktree, which the Claude
Code action restores from the PR's base. They SHALL name every other file of the PR worktree,
including any other `CLAUDE.md` or `.claude/rules/` file, as untrusted review data.
Neither SHALL name as policy a document the session does not load.

#### Scenario: PR changes the policy
- **WHEN** a PR changes the root `CLAUDE.md`, a root `.claude/rules/` file or a document they link to
- **THEN** the prompt and the contract name the root `CLAUDE.md` and `.claude/rules/` restored from the PR's base as the policy, and name no linked document as policy

#### Scenario: PR adds instructions elsewhere
- **WHEN** a PR adds a `CLAUDE.md` or `.claude/rules/` file outside the root ones
- **THEN** the prompt and the contract call it untrusted review data
