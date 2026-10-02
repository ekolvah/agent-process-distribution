## MODIFIED Requirements

### Requirement: ci_check is the one command every gate runs
One command, `ci_check`, SHALL be what the pre-push git hook and the CI workflow run; there
is no second list of checks. `ci_check` SHALL run the `pre-commit`-stage hooks of
`.pre-commit-config.yaml` over all files, so the checks run after an edit are part of the gate.

#### Scenario: Push
- **WHEN** a branch is pushed
- **THEN** the pre-push hook runs `ci_check` as its only check, and CI runs the same command

#### Scenario: Edit-time check in the gate
- **WHEN** a file fails a `pre-commit`-stage hook of `.pre-commit-config.yaml`
- **THEN** `ci_check` exits non-zero with that hook's output, and runs no `pre-push`-stage hook

### Requirement: Shift-left feedback in Claude
A PostToolUse hook SHALL run the project's `pre-commit`-stage hooks of `.pre-commit-config.yaml`
on a file right after it is edited and surface their findings to the agent; a PreToolUse hook
SHALL deny shell navigation of the repository (`cat`, `grep`, `find`, `sed -n`, whole-file
reads over the budget) and name the cheaper route.

#### Scenario: Lint error
- **WHEN** an edit introduces an error that a `pre-commit`-stage hook of the project reports
- **THEN** the agent sees the finding before its next tool call

#### Scenario: Shell navigation
- **WHEN** a shell command contains a denied navigation stage anywhere in a pipeline
- **THEN** the command is denied and the response names the tool to use instead

### Requirement: A broken hook is visible
A hook that cannot do its job (`pre-commit` missing or its config unreadable, git state
unreadable) SHALL surface a marker or fail closed, never pass silently.

#### Scenario: Linter cannot run
- **WHEN** `pre-commit` is not on `PATH`, or cannot load the project's `.pre-commit-config.yaml`
- **THEN** the agent sees a marker naming the cause instead of a clean result
