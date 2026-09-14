# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

### Requirement: Three native delivery channels
The process SHALL be delivered through three native channels: a Claude Code plugin
(`.claude-plugin/`, this repository as its marketplace), Codex skills (`.agents/skills/`),
and reusable GitHub workflows (`.github/workflows/reusable-*.yml`) that a consumer calls
from thin caller workflows.

#### Scenario: Consumer callers are thin
- **WHEN** a consumer project is rendered
- **THEN** its workflows only call the reusable workflows and carry no gate logic of their own

### Requirement: CI runs the trusted driver, not the PR's copy
The reusable quality workflow SHALL execute the process driver from the trusted default
branch against the PR worktree, so a PR cannot change what checks it.

#### Scenario: Quality check on a PR
- **WHEN** the quality workflow runs for a PR
- **THEN** the driver comes from the default branch and the PR's files are only its input

### Requirement: The process footprint lives under one root
Everything a consumer receives SHALL live under one process-owned root; the consumer's own
files are never touched, and publisher-only tests never reach a consumer.

#### Scenario: Rendered payload
- **WHEN** the process is rendered into a project
- **THEN** every rendered file is under the process root and no publisher test is among them

### Requirement: This repository dogfoods its own process
This repository SHALL carry the same rendered payload a consumer receives, so every process
change is exercised here before a consumer sees it.

#### Scenario: Process change
- **WHEN** the payload changes in this repository
- **THEN** this repository's own sessions and CI run the changed payload
