## MODIFIED Requirements

### Requirement: Shift-left feedback in Claude
A PostToolUse hook SHALL run the project's `pre-commit`-stage hooks of `.pre-commit-config.yaml`
on a file right after it is edited and surface their findings to the agent; a PreToolUse hook
SHALL deny shell navigation of the repository (`cat`, `grep`, `find`, `sed -n`, whole-file
reads over the budget) and name the cheaper route.

#### Scenario: Lint error
- **WHEN** an edit introduces an error that a `pre-commit`-stage hook of the project reports
- **THEN** the agent sees the finding before its next tool call

#### Scenario: Shell navigation
- **WHEN** a shell command contains a denied navigation stage anywhere in a pipeline, or inside a shell's `-c` command string with the flag alone or in a short-option cluster (`bash -lc`, `sh -ec`)
- **THEN** the command is denied and the response names the tool to use instead
