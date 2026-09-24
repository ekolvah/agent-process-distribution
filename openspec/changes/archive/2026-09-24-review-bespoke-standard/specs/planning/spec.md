## MODIFIED Requirements

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
script or check without an observed problem it closes, SHALL each be a finding class. Each
script, check or non-test file the plan adds SHALL be an entry of the file's `additions`
with the problem it closes, the established standard for its job and why it does not fit;
an `approve` with an entry whose problem is not an issue, PR or run reference, or whose
standard is none, SHALL NOT validate. On
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

#### Scenario: Addition without evidence
- **WHEN** an `approve` review lists an addition whose problem is not an issue, PR or run reference, or whose standard is none, n/a or a dash, or lacks the `additions` key
- **THEN** `create_tracking_issue` and `start_change` exit 2 naming the validation error, and nothing is created

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
