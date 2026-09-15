# planning Specification

## Purpose
How the process gets high-quality plans out of agents, and what the person approves before
implementation starts.

## Requirements

### Requirement: A change is the unit of planning
Substantive work SHALL start as an OpenSpec change created by `/opsx:propose`:
`openspec/changes/<name>/` with proposal, spec deltas, design, architect review and tasks.
A GitHub issue SHALL track the change (title, change name, priority) and is its Project item.

#### Scenario: New task
- **WHEN** the person asks for a task
- **THEN** a change directory exists and validates before any code is written

### Requirement: The planner reads before writing and asks instead of guessing
The planner SHALL read the code and prior art before writing a plan, and SHALL ask the
person when a decision is theirs. Project context reaches it from `openspec/config.yaml`.

#### Scenario: Ambiguous scope
- **WHEN** the request leaves a scope decision open
- **THEN** the planner asks before writing the proposal

### Requirement: Architect review is an artifact of the change
Every change SHALL carry an `architect-review` artifact as its last planning artifact
(schema: proposal → specs → design → tasks → architect-review; `apply` requires both), written
by the `architect-reviewer` subagent in Claude and as a self-review in Codex, against
`principles.md` §I–VII and the scenario → test map of `tasks.md`.

#### Scenario: Review finding
- **WHEN** the review finds a simpler design or a scenario missing from the map
- **THEN** the finding is in `architect-review.md` before the person approves

#### Scenario: Rework verdict
- **WHEN** `architect-review.md` says `rework`
- **THEN** the propose run applies or answers the findings and reviews again, and no
  delivery task runs until the verdict is `approve`

### Requirement: Human approval is the gate
The person SHALL approve the change; nothing implements before the person runs
`/opsx:apply <change>` (`$openspec-apply-change`). The only automated check on a plan SHALL be `openspec validate --strict`.

#### Scenario: Validator scope
- **WHEN** a change validates
- **THEN** no other script judges its content; the person does

### Requirement: A behaviour change carries its spec delta
A PR that changes target behaviour SHALL carry the change's spec delta and SHALL archive
the change before merge: `finish_change` runs `openspec archive <change>` once checks are
green and no thread is unresolved, and a fix after that is a later commit on the same PR.
So `openspec/specs/` on `main` is what is implemented and no second PR is needed.

#### Scenario: Behaviour change
- **WHEN** a PR changes what the process does
- **THEN** the same PR contains the delta and the archived change

### Requirement: Bugs are reproduced before the fix is designed
For a bug, the proposal SHALL record the reproduction (the failing test, or the exact
observation when a test needs project-specific capture) and the root cause before the
design; this is a `config.yaml` rule on `proposal`. The core SHALL NOT prescribe how
evidence is captured.

#### Scenario: Bug change
- **WHEN** the planner proposes a bug fix
- **THEN** the proposal states the reproduction and root cause before the design exists

### Requirement: Every scenario maps to a test
Every scenario in the change's spec delta SHALL map to a named test in `tasks.md`, or carry
`n/a: <reason>`; a scenario without a test SHALL be an architect-review finding. When the map
names no test, the RED group SHALL be one task recording `no RED: <reason>`.

#### Scenario: Unmapped scenario
- **WHEN** a scenario has neither a test nor `n/a`
- **THEN** the architect review reports it

### Requirement: No per-label section sets and no discovery role
The core SHALL NOT have per-label artifact sets, a separate `discovery` role or a
fixture-capture script; reproduction is a step of planning.

#### Scenario: Label change
- **WHEN** an issue's labels change
- **THEN** the set of required artifacts does not
