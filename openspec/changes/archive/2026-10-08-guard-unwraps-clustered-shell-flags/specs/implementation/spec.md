## MODIFIED Requirements

### Requirement: Shift-left feedback in Claude
A PostToolUse hook SHALL run the project's `pre-commit`-stage hooks of `.pre-commit-config.yaml`
on a file right after it is edited and surface their findings to the agent; a PreToolUse hook
SHALL deny a whole-file `Read` over the read budget and name the cheaper slice or search.

#### Scenario: Lint error
- **WHEN** an edit introduces an error that a `pre-commit`-stage hook of the project reports
- **THEN** the agent sees the finding before its next tool call

#### Scenario: Shell navigation
- **WHEN** a shell command reads the repository (`cat`, `grep`, `find`, `sed -n`)
- **THEN** no PreToolUse navigation hook denies it

#### Scenario: Whole-file read over the budget
- **WHEN** the agent reads a whole file larger than the read budget
- **THEN** the read is denied and the response names the slice or search to use instead
