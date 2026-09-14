## Purpose
What reviews a PR, what blocks a merge, and how the process protects the default branch
from agent mistakes.

## ADDED Requirements

### Requirement: Merge gates are GitHub-native
The only automated merge gates SHALL be: required checks from the reusable workflow,
`required_conversation_resolution`, PR required, no direct push — applied as a ruleset JSON
kept in this repository and installed once by `init`.

#### Scenario: Direct push
- **WHEN** anyone pushes to the default branch
- **THEN** the ruleset rejects it

### Requirement: Local safety is a deny-list
The plugin's `settings.json` SHALL deny force-push and push to the default branch; the
ruleset is the authoritative barrier.

#### Scenario: Force push
- **WHEN** an agent runs `git push --force`
- **THEN** the command is denied locally
