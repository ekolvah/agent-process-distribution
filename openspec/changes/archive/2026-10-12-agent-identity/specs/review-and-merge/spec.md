## ADDED Requirements

### Requirement: The person approves
Where `agent_identity` has run, GitHub SHALL refuse to merge a PR into the default branch until
someone other than its author approves it, whatever the command or API and whoever merges. A
push after the approval SHALL dismiss it. The release PR gets its approval from the release
workflow ("Releases go through release-please").

#### Scenario: Merge from Claude Code
- **WHEN** an agent whose session carries the identity's `GH_TOKEN` runs `gh pr merge` or `gh api -X PUT repos/<repo>/pulls/<N>/merge` on its own PR that the person has not approved
- **THEN** GitHub refuses it with a repository rule violation, and the PR stays open for the person

## REMOVED Requirements

### Requirement: Local safety in Claude Code
**Reason**: Replaced by "The person approves", with the git guard (distribution, REMOVED "The
plugin ships the git guard").

**Migration**: As for the git guard.
