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

### Requirement: Human approval is the gate
The person SHALL approve the change; nothing implements before the person runs
`/opsx:apply <change>` (`$openspec-apply-change`). The only automated check on a plan SHALL be `openspec validate --strict`.

#### Scenario: Validator scope
- **WHEN** a change validates
- **THEN** no other script judges its content; the person does

### Requirement: A behaviour change carries its spec delta
A PR that changes target behaviour SHALL carry the change's spec delta and SHALL archive
the change before the PR opens: `archive_change` runs `openspec archive <change>` once
`ci_check` is green, so the head the review reads is the archived one, and a fix after that
is a later commit on the same PR. So `openspec/specs/` on `main` is what is implemented and
no second PR is needed.

#### Scenario: Behaviour change
- **WHEN** a PR changes what the process does
- **THEN** the PR contains the delta and the archived change from its first head

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

### Requirement: Architect review is the last step of the propose run
The `tasks` rule of `openspec/config.yaml` SHALL end the propose run with the architect
review: the `architect-reviewer` subagent in Claude, the planner as a self-review in Codex,
writes `openspec/changes/<change>/architect-review.md` (Verdict, Findings, Scenario coverage)
against `principles.md` §I–VII and the scenario → test map of `tasks.md`. The review contract
SHALL live in that rule, not in a schema: the schema is the unmodified `spec-driven`. On
`rework` the planner SHALL apply or answer every finding in the artifact it names and the
review SHALL run again. On `approve` the planner SHALL make sure the tracking issue exists
(when the change has none: ask the person for the priority, then `gh issue create`) and set
its Status to `Planned` with the priority; the propose run ends there. The apply gate SHALL
be the first delivery task of `tasks.md` (the verdict line starts with `approve`), since
artifact status is file existence only.

#### Scenario: Review finding
- **WHEN** the review finds a simpler design or a scenario missing from the map
- **THEN** the finding is in `architect-review.md` before the person approves

#### Scenario: Rework verdict
- **WHEN** `architect-review.md` says `rework`
- **THEN** the propose run applies or answers the findings and reviews again, and no
  delivery task runs until the verdict is `approve`

#### Scenario: Plan approved
- **WHEN** `architect-review.md` says `approve`
- **THEN** the tracking issue exists and is a Project item in `Planned` with its priority before the propose run reports the artifacts ready

#### Scenario: Review archives with the change
- **WHEN** a change whose directory holds `architect-review.md` is archived
- **THEN** the file is in `openspec/changes/archive/<date>-<change>/` with the four artifacts
