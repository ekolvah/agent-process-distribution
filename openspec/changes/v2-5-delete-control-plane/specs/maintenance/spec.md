## ADDED Requirements

### Requirement: A script is justified by an observed, repeated failure
A single failure SHALL be fixed by a line in the skill or a `config.yaml` rule; the second
occurrence earns the script.

#### Scenario: First failure
- **WHEN** a failure is observed once
- **THEN** the fix is a rule line, not a script

### Requirement: Core scripts are stack-agnostic
Core scripts SHALL use `gh`, `git`, `openspec` and the standard library only; anything
stack-specific lives in the consumer's `AGENTS.md` or `ci_check`.

#### Scenario: Non-Python consumer
- **WHEN** the process is installed in a TypeScript project
- **THEN** no core script needs a Python package or a stack-specific tool

### Requirement: Size budget
Core scripts SHALL be ≤ 1 000 lines and workflows ≤ 150 lines. Exceeding it is a finding,
not a default.

#### Scenario: Budget exceeded
- **WHEN** a PR pushes core scripts over the budget
- **THEN** the review raises it as a finding

### Requirement: Deterministic rules live in scripts
Deterministic rules SHALL live in scripts with exit codes, prohibitions in deny-lists or
hooks, never in prose the agent has to remember — except where the carrier has no hook
mechanism (Codex): there the prohibition is an `AGENTS.md` sentence, and an observed
violation is what justifies a mechanism.

#### Scenario: New prohibition
- **WHEN** a prohibition is added to the process
- **THEN** it is a deny-list or hook entry for Claude Code and an `AGENTS.md` sentence only for a carrier without hooks

### Requirement: No internal API compatibility
Only the skills' user-facing commands and the reusable workflow inputs SHALL be contracts;
internal script APIs MAY change without notice.

#### Scenario: Internal refactor
- **WHEN** a script's internal function signature changes
- **THEN** no migration note is required
