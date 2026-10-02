## ADDED Requirements

### Requirement: The plugin ships the memory checkpoint
After an `Edit` or `Write` of a file under the agent's auto-memory directory
(`.claude/projects/<project>/memory/`), the plugin's hook SHALL show the agent a reminder
without undoing the write. The reminder SHALL name the file and ask whether every session and
every person working on the repository needs the fact; if so, it SHALL ask the agent to move
the fact into the repository. Any
other path SHALL produce no output. This repository's own post-edit hook SHALL carry no memory
check.

#### Scenario: Memory write in an adopted consumer
- **WHEN** the plugin's `PostToolUse` hook runs with a project directory that carries `.github/workflows/agent-process.yml` and no copy of the check, for a `Write` of a file under `.claude/projects/<project>/memory/` given with either path separator
- **THEN** it exits 2 with stderr naming the file, asking whether every session and every person needs the fact, and if so to move it into the repository

#### Scenario: Write outside auto-memory
- **WHEN** the same hook runs for a file of the repository, including one under `.claude/rules/`, or for a payload without a file path
- **THEN** it exits 0 with no output

#### Scenario: Repository hook carries no memory check
- **WHEN** this repository's own post-edit hook runs for a write under `.claude/projects/<project>/memory/`
- **THEN** it exits 0 with no output
