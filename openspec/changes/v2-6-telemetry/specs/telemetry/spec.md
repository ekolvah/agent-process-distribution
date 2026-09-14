## Purpose
How token efficiency of the process is measured, which metrics compare two versions of the
process, and where that measurement lives.

## ADDED Requirements

### Requirement: Measurement is an optional owner-side module
Nothing in the plugin, the skills or the reusable workflows SHALL depend on or ship the
measurement module.

#### Scenario: Consumer without telemetry
- **WHEN** a consumer installs the process without the owner module
- **THEN** every role works unchanged

### Requirement: One collector with project, task and attempt labels
Both agents SHALL export OTLP metrics through one local collector that attaches project,
task and attempt labels; project identity rides the resource attributes, task and attempt
identity are created by the launcher before the agent starts.

#### Scenario: Two agents on one task
- **WHEN** Claude plans and Codex implements the same change
- **THEN** both runs carry the same task label

### Requirement: Versions are compared on per-PR metrics
Process versions SHALL be compared on tokens per merged PR by role (plan / implement / fix),
cycle time per PR, review rounds per PR, share of PRs merged without a fixer commit, and
agent turns per issue — never on raw token sums.

#### Scenario: v1 vs v2 report
- **WHEN** the comparison is produced
- **THEN** every metric is per merged PR

### Requirement: Every task records its process version
Every measured task SHALL record the process version tag it ran under.

#### Scenario: Filtering
- **WHEN** the owner filters tasks by version
- **THEN** each task appears under exactly one version

### Requirement: Bypassed launches are visible
A launch that bypasses the launcher SHALL be labelled `unassigned`, never charged to the
previous task.

#### Scenario: Direct launch
- **WHEN** an agent is started without the launcher
- **THEN** its tokens appear under `unassigned`

### Requirement: No session-level accounting
The module SHALL NOT account per session: one session spans several issues, one issue spans
several sessions.

#### Scenario: One session, two issues
- **WHEN** a session works on two issues
- **THEN** tokens are attributed to each task, not to the session
