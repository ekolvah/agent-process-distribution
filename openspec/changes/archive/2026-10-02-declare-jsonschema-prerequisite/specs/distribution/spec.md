## ADDED Requirements

### Requirement: The plugin installs its runtime environment
At session start, the plugin SHALL install its runtime manifest `.agent-process/requirements.txt`
into a virtual environment under `${CLAUDE_PLUGIN_DATA}` named by the manifest's content, when
no completed environment of that name exists or its interpreter fails `pip check`, and SHALL then export `AGENT_PROCESS_PYTHON`, the
environment's interpreter, through `CLAUDE_ENV_FILE`. An install SHALL NOT modify an environment
of another manifest. The launcher SHALL run every script with `AGENT_PROCESS_PYTHON` when it is
set, and with `python` otherwise. A failed install, or a hook run without `CLAUDE_PLUGIN_DATA` or
`CLAUDE_ENV_FILE`, SHALL exit 0 with an `agent-process plugin environment not installed` marker
to the person and to the agent; a failed install SHALL be retried at the next session start.

#### Scenario: First session
- **WHEN** the plugin's `SessionStart` hook runs with an empty data directory
- **THEN** it exits 0 with empty stdout, the environment's interpreter exists, and `CLAUDE_ENV_FILE` exports `AGENT_PROCESS_PYTHON` naming it

#### Scenario: Manifest unchanged
- **WHEN** the hook runs again with the same manifest
- **THEN** it does not reinstall the environment and exports `AGENT_PROCESS_PYTHON` again

#### Scenario: Install fails
- **WHEN** the manifest cannot be installed
- **THEN** the hook exits 0, its output names `agent-process plugin environment not installed` to the person and to the agent, and the next run installs again

#### Scenario: Broken environment
- **WHEN** the hook runs and the completed environment's interpreter cannot run
- **THEN** it reinstalls that environment and exports its interpreter

#### Scenario: Hook variables absent
- **WHEN** the hook runs without `CLAUDE_PLUGIN_DATA` or without `CLAUDE_ENV_FILE`
- **THEN** it exits 0 and its output names `agent-process plugin environment not installed` and the missing variable

#### Scenario: Manifest changed
- **WHEN** the hook runs with a manifest different from the one an existing environment was installed from
- **THEN** it installs a second environment, exports that one, and leaves the first unchanged

#### Scenario: Launcher uses the session interpreter
- **WHEN** `agent-process <script>` runs with `AGENT_PROCESS_PYTHON` set
- **THEN** the script runs under that interpreter

## MODIFIED Requirements

### Requirement: Plugin hooks act only in adopted repositories
Every tool hook command of the plugin SHALL exit 0 with no output when the session's project
directory has no `.github/workflows/agent-process.yml`. The `SessionStart` environment install
is not gated: `init` and the first propose run of a consumer can share one session.

#### Scenario: Unadopted repository
- **WHEN** any tool hook command of the plugin runs with a project directory that has no `.github/workflows/agent-process.yml`, for an input its policy would deny
- **THEN** it exits 0 with empty stdout
