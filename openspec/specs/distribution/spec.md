# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
The reusable quality workflow SHALL execute the process driver from the trusted default
branch against the PR worktree, so a PR cannot change what checks it.

#### Scenario: Quality check on a PR
- **WHEN** the quality workflow runs for a PR
- **THEN** the driver comes from the default branch and the PR's files are only its input

### Requirement: The process footprint is one root plus a closed exception set
Everything a consumer receives SHALL live under `.agent-process/`, except the paths the
tools themselves mandate: the thin caller workflows and the PR template under `.github/`,
`AGENTS.md`, `.gitignore`, the agent-tool configuration under `.agents/`, `.claude/` and
`.codex/`, and the consumer tests under `tests/agent_process/`. That set is closed; the
consumer's other files are never touched, and publisher-only tests never reach a consumer.

#### Scenario: Rendered payload
- **WHEN** the process is rendered into a project
- **THEN** every rendered file is under the process root or in the closed exception set, and no publisher test is among them

### Requirement: This repository dogfoods its own process
This repository SHALL carry the same rendered payload a consumer currently receives and
SHALL expose and enable the shared Claude plugin/skill package that later distribution steps
will install. Repository sessions and publisher tests SHALL exercise the shared skill source,
its portable scripts, its OpenSpec rule pointers, and its package-version identity before a
consumer installation path is added. Repository-only settings and v1 process files SHALL NOT
be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its current consumer payload and delivery gates remain intact
