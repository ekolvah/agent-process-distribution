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
This repository SHALL carry the same rendered payload a consumer receives, so every process
change is exercised here before a consumer sees it.

#### Scenario: Process change
- **WHEN** the payload changes in this repository
- **THEN** this repository's own sessions and CI run the changed payload
