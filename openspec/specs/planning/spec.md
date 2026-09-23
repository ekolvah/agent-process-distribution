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
writes `openspec/changes/<change>/architect-review.json` against `principles.md` §I–VII and
the scenario → test map of `tasks.md`. The file SHALL be valid against
`skills/agent-process/architect-review.schema.json`: the verdict, the reviewer, one entry per finding
class with its evidence and `ok` or the finding, and the scenario coverage; the classes and
the evidence each requires are the schema's. The review contract SHALL live in the shared
skill and that schema, not in a schema of OpenSpec: the OpenSpec schema is the unmodified
`spec-driven`. A rule or spec sentence longer than the words its tests assert, and a new
script or check without an observed problem it closes, SHALL each be a finding class. On
`rework` the planner SHALL apply or answer every finding in the artifact it names and the
review SHALL run again. On `approve` the planner SHALL run `create_tracking_issue <change>`
— with the priority asked from the person when the change has no tracking issue yet — which
SHALL exit 2 without creating anything when the file is not valid or its verdict is not
`approve`, the errors going back to the reviewer; otherwise it creates the issue from the
proposal, sets its Status to `Planned` with the priority and writes the number into
`tasks.md`, or, when `tasks.md` already carries the number, sets `Planned` alone and refuses
a priority; the propose run ends there. The apply gate SHALL be the first delivery task of
`tasks.md` (the file valid, its `verdict` `approve`), since artifact status is file
existence only.

#### Scenario: Review finding
- **WHEN** the review finds a simpler design or a scenario missing from the map
- **THEN** the finding is in `architect-review.json` before the person approves

#### Scenario: Review class without evidence
- **WHEN** the reviewer writes `architect-review.json` with a class missing, an empty evidence, or a finding without its four fields
- **THEN** `create_tracking_issue` exits 2 naming each validation error, creates no issue, and the propose run does not report the artifacts ready

#### Scenario: Over-long rule or bespoke check
- **WHEN** a plan carries a rule or spec sentence longer than the words its tests assert, or a new script or check without an observed problem it closes
- **THEN** the architect review reports it as a finding of its class before the person approves

#### Scenario: Rework verdict
- **WHEN** `architect-review.json` says `rework`
- **THEN** the propose run applies or answers the findings and reviews again, and no
  delivery task runs until the verdict is `approve`

#### Scenario: Plan approved
- **WHEN** `architect-review.json` says `approve`
- **THEN** the tracking issue exists and is a Project item in `Planned` with its priority before the propose run reports the artifacts ready

#### Scenario: Existing tracking issue
- **WHEN** `create_tracking_issue` runs on a change whose `tasks.md` already carries the issue number
- **THEN** it creates no issue, refuses a priority, and moves that issue to `Planned`

#### Scenario: Review archives with the change
- **WHEN** a change whose directory holds `architect-review.json` is archived
- **THEN** the file is in `openspec/changes/archive/<date>-<change>/` with the four artifacts

### Requirement: Platform facts are observed before a design rests on them
A proposal whose design rests on a platform behaviour — an event, a permission, a merge
rule, a token scope, a CLI flag — SHALL rest on an observation of that behaviour made
before the proposal is written, and SHALL record it under **Why** or in `design.md` beside
the decision that rests on it: the reference page (its URL and the sentence) or the run id
or command and its output; a listing, a name or an inference SHALL NOT count, and an
observation already on record (an ADR entry, an archived change) is pointed at, not
repeated. This is a `config.yaml` rule on `proposal`. A platform behaviour a design rests
on that is asserted without an observation SHALL be an architect-review finding.

#### Scenario: Design on a platform behaviour
- **WHEN** the planner proposes a design that rests on a platform behaviour
- **THEN** the proposal's **Why** or the design carries the observation — the reference page or the run id / command output — beside the decision that rests on it

#### Scenario: Asserted platform fact
- **WHEN** a design rests on a platform behaviour and no observation stands beside it
- **THEN** the architect review reports it as a finding before the person approves

### Requirement: A replaced input lists its failure modes and its catcher
A design that replaces a project-declared input with one the caller supplies, or drops a
guard, SHALL list beside that decision the failure modes of the new input (when one is
replaced), what the component stops proving, and for each dropped proof the concrete
step of the delivery flow that catches it — which script, which run, on which head — not
a role or the platform in general. This is a `config.yaml` rule on `design`. A replaced
input or a dropped guard without the list, and a named catcher the architect review cannot
trace to a step the flow reaches in the described case, SHALL each be an
architect-review finding.

#### Scenario: Replaced input designed
- **WHEN** the planner proposes a design that replaces a project-declared input with a caller-supplied one or drops a guard
- **THEN** the design lists, beside the decision, the failure modes of the new input (when one is replaced), the proofs the component loses and the delivery-flow step that catches each

#### Scenario: Untraceable catcher
- **WHEN** a design names a catcher the delivery flow does not reach in the described case, or replaces an input without the list
- **THEN** the architect review reports it as a finding before the person approves
