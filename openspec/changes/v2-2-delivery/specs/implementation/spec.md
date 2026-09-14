## ADDED Requirements

### Requirement: ci_check is the single source of truth and runs the whole suite
The project's `ci_check` SHALL run the whole test suite, never a changed-files subset; the
pre-push git hook and the reusable workflow SHALL run the same command on every push.

#### Scenario: Push
- **WHEN** a branch is pushed
- **THEN** the pre-push hook and the workflow both run `ci_check` on the whole suite

### Requirement: Shift-left feedback in Claude
A PostToolUse hook SHALL run the linter declared for the edited file's extension right after
the edit; a PreToolUse hook SHALL give the cheaper navigation route when a shell command
reads a file.

#### Scenario: Lint error
- **WHEN** an edit introduces a lint error
- **THEN** the agent sees it before the next tool call

### Requirement: Stop hook names the next command
A Stop hook SHALL block the end of a turn only when the current branch has an open PR with
pending checks or unresolved threads, and SHALL name the next command.

#### Scenario: Clean PR
- **WHEN** the PR is green with no unresolved threads
- **THEN** the turn ends

### Requirement: Principles reach the agent as one short file
`principles.md` SHALL reach the agent through the plugin's rules as one short file.

#### Scenario: Session start
- **WHEN** a session starts in a consumer
- **THEN** the principles are loaded from one file of the plugin
