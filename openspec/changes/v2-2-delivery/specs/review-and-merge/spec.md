## Purpose
What reviews a PR, what blocks a merge, and how the process protects the default branch
from agent mistakes.

## ADDED Requirements

### Requirement: Merge gates are GitHub-native
The only automated merge gates SHALL be: required checks from the reusable workflow,
`required_conversation_resolution`, PR required, no direct push — applied as a ruleset JSON
kept in this repository and installed once by `init`. The required check SHALL be anchored to
the workflow definition on the default branch: the caller workflow runs on
`pull_request_target` (definition read from the base branch, PR head checked out by SHA,
`permissions: contents: read`, no secrets), so a PR that edits
`.github/workflows/agent-process.yml` cannot change what the required check runs; where the
plan offers ruleset-required workflows, `init` MAY use them instead.

#### Scenario: Direct push
- **WHEN** anyone pushes to the default branch
- **THEN** the ruleset rejects it

#### Scenario: Caller workflow edited in a PR
- **WHEN** a PR replaces the caller workflow with a no-op job of the same name
- **THEN** the required check still runs the default-branch definition and the edit is visible in the diff

### Requirement: Local safety is a deny-list
The plugin's `settings.json` SHALL deny force-push and push to the default branch; the
ruleset is the authoritative barrier.

#### Scenario: Force push
- **WHEN** an agent runs `git push --force`
- **THEN** the command is denied locally
