# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

### Requirement: Layered delivery through Copier
The provider-neutral core and the Codex skills (`.agents/skills/`) SHALL reach a consumer as
one Copier render; the Claude adapter files SHALL reach it through the Claude Code plugin
marketplace (`.claude-plugin/`, this repository as the marketplace). CI logic is the core's
one referenced component: pinned reusable GitHub workflows
(`.github/workflows/reusable-*.yml`) that the thin caller workflows in the Copier payload
call.

#### Scenario: Consumer callers are thin
- **WHEN** a consumer project is rendered
- **THEN** its workflows only call the reusable workflows and carry no gate logic of their own

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
