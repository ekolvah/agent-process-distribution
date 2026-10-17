## MODIFIED Requirements

### Requirement: The planner reads before writing and asks instead of guessing
The planner SHALL read the code and prior art before writing a plan: the usage guidance of
each external tool, model or API the design is built around or that is new to the
repository, and the standard approach to the problem, recorded under a `## Standard approach`
heading of `design.md` or `proposal.md` with each source's URL, or `none found:` with what was
searched. It SHALL ask the person when a decision is theirs. Project context reaches it from `openspec/config.yaml`.

#### Scenario: Ambiguous scope
- **WHEN** the request leaves a scope decision open
- **THEN** the planner asks before writing the proposal

#### Scenario: Design on an external tool
- **WHEN** the planner designs a change built around an external tool, model or API
- **THEN** the `## Standard approach` section cites that tool's usage guidance and the standard approach to the problem with their URLs, or `none found:` with what was searched

### Requirement: Human approval is the gate
The person SHALL approve the change; nothing implements before the person runs
`/opsx:apply <change>` (`$openspec-apply-change`). The automated checks on a plan SHALL be
`openspec validate --strict` and the propose tail's check that the `## Standard approach`
section is present with a URL or `none found:`, which checks its form only.

#### Scenario: Validator scope
- **WHEN** a change validates
- **THEN** no script judges whether its content is right; the person does

### Requirement: Architect review is the last step of the propose run
The `tasks` rule of `openspec/config.yaml` SHALL end the propose run with the architect
review: the `architect-reviewer` subagent writes `openspec/changes/<change>/architect-review.json` against §I–VII of `always-on.md` and
the scenario → test map of `tasks.md`. The file SHALL be valid against
`skills/agent-process/architect-review.schema.json`: the verdict, the reviewer, the round (1 on the change's first review, otherwise one more than the file it replaces), one entry per finding
class with its evidence and `ok` or the finding, and the scenario coverage; the classes and
the evidence each requires are the schema's. The review contract SHALL live in the shared
skill and that schema, not in a schema of OpenSpec: the OpenSpec schema is the unmodified
`spec-driven`. A rule or spec sentence longer than the words its tests assert, a
`## Standard approach` whose source is not the standard approach to the problem or whose
`none found` is unconvincing, or a new script or check whose `design.md` decision does not name the problem it closes and the
standard it weighed, SHALL each be a finding class. On
`rework` the planner SHALL apply or answer every finding in the artifact it names and the
review SHALL run again. On `approve` the planner SHALL run `create_tracking_issue <change>`
— with the area the planner chose from the Project's `Area` options when the change has no tracking issue yet — which
SHALL exit 2 without creating or moving anything when the file is not valid or its verdict is
not `approve`, the errors going back to the reviewer, or when neither `proposal.md` nor
`design.md` has a `## Standard approach` section (up to the next `##` heading) carrying a URL or `none found:` with text,
which goes back to the planner; otherwise it creates the issue from the
proposal, sets its Status to `Planned` with the area and writes the number into
`tasks.md`, or, when `tasks.md` already carries the number, sets `Planned` alone and refuses
an area; the propose run ends there. The apply gate SHALL be the first delivery task of
`tasks.md` (the file valid, its `verdict` `approve`), since artifact status is file
existence only.

#### Scenario: Review finding
- **WHEN** the review finds a simpler design or a scenario missing from the map
- **THEN** the finding is in `architect-review.json` before the person approves

#### Scenario: Review class without evidence
- **WHEN** the reviewer writes `architect-review.json` with a class missing, an empty evidence, or a finding without its four fields
- **THEN** `create_tracking_issue` exits 2 naming each validation error, creates no issue, and the propose run does not report the artifacts ready

#### Scenario: Over-long rule or bespoke check
- **WHEN** a plan carries a rule or spec sentence longer than the words its tests assert, a `## Standard approach` whose source is not the standard approach to the problem or whose `none found` is unconvincing, or a new script or check whose `design.md` decision does not name the problem it closes and the standard it weighed
- **THEN** the architect review reports it as a finding of its class before the person approves

#### Scenario: Plan without a standard approach
- **WHEN** `create_tracking_issue` runs on an `approve` review whose change has no `## Standard approach` section in `proposal.md` or `design.md`, or one with neither a URL nor `none found:` with text
- **THEN** it exits 2 naming the section, and creates no issue and moves no status

#### Scenario: Plan without a prior issue
- **WHEN** an `approve` review of a change with no tracking issue yet carries every class `ok` and no reference to a problem
- **THEN** `create_tracking_issue` creates the issue

#### Scenario: Addition without evidence
- **WHEN** a review carries an `additions` key
- **THEN** `create_tracking_issue` and `start_change` exit 2 naming `additions` as not allowed, and nothing is created

#### Scenario: Rework verdict
- **WHEN** `architect-review.json` says `rework`
- **THEN** the propose run applies or answers the findings and reviews again, and no
  delivery task runs until the verdict is `approve`

#### Scenario: Plan approved
- **WHEN** `architect-review.json` says `approve`
- **THEN** the tracking issue exists and is a Project item in `Planned` with its area before the propose run reports the artifacts ready

#### Scenario: Existing tracking issue
- **WHEN** `create_tracking_issue` runs on a change whose `tasks.md` already carries the issue number
- **THEN** it creates no issue, refuses an area, and moves that issue to `Planned`

#### Scenario: Review archives with the change
- **WHEN** a change whose directory holds `architect-review.json` is archived
- **THEN** the file is in `openspec/changes/archive/<date>-<change>/` with the four artifacts

#### Scenario: Review round
- **WHEN** the reviewer reviews a change again after `rework`
- **THEN** the new `architect-review.json` carries a `round` one more than the file it replaces, and a review without `round` fails validation naming it
