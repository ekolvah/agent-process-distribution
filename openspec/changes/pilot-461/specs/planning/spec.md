## ADDED Requirements

### Requirement: Planning starts from the standard approach
Before designing, the planner SHALL read the usage guidance of each external tool, model or API
the change touches and SHALL record under `## Standard approach` in `design.md` or
`proposal.md` the industry-standard approach to the problem with its source: a URL, or
`none found:` followed by what was searched. The architect review's
`bespoke` class SHALL judge, for every plan, whether the source is the standard approach and why
the design follows or departs from it.

#### Scenario: Departure from the standard
- **WHEN** a plan lacks the section, its source is not the standard approach to the problem, or the design departs from it without saying why
- **THEN** the architect review reports it as a `bespoke` finding before the person approves

## MODIFIED Requirements

### Requirement: Architect review is the last step of the propose run
The `tasks` rule of `openspec/config.yaml` SHALL end the propose run with the architect
review: the `architect-reviewer` subagent writes `openspec/changes/<change>/architect-review.json` against §I–VII of `always-on.md` and
the scenario → test map of `tasks.md`. The file SHALL be valid against
`skills/agent-process/architect-review.schema.json`: the verdict, the reviewer, the round (1 on the change's first review, otherwise one more than the file it replaces), one entry per finding
class with its evidence and `ok` or the finding, and the scenario coverage; the classes and
the evidence each requires are the schema's. The review contract SHALL live in the shared
skill and that schema, not in a schema of OpenSpec: the OpenSpec schema is the unmodified
`spec-driven`. A rule or spec sentence longer than the words its tests assert, and a new
script or check whose `design.md` decision does not name the problem it closes and the
standard it weighed, SHALL each be a finding class. On
`rework` the planner SHALL apply or answer every finding in the artifact it names and the
review SHALL run again. On `approve` the planner SHALL run `create_tracking_issue <change>`
— with the area the planner chose from the Project's `Area` options when the change has no tracking issue yet — which
SHALL exit 2 without creating or moving anything when the file is not valid, its verdict is not
`approve`, or `## Standard approach` is missing or out of form, the errors going back to the
reviewer; otherwise it creates the issue from the
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
- **WHEN** a plan carries a rule or spec sentence longer than the words its tests assert, or a new script or check whose `design.md` decision does not name the problem it closes and the standard it weighed
- **THEN** the architect review reports it as a finding of its class before the person approves

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

#### Scenario: Standard approach missing
- **WHEN** `create_tracking_issue` runs on an approved change where neither `design.md` nor `proposal.md` has `## Standard approach` in form (missing, plain text, or `none found:` with nothing after it)
- **THEN** it exits 2 naming `## Standard approach`, and no issue is created or moved

#### Scenario: Standard approach recorded
- **WHEN** the section in `design.md` or `proposal.md` carries a URL or `none found:` and what was searched
- **THEN** `create_tracking_issue` creates or moves the tracking issue as it does without the gate


### Requirement: Human approval is the gate
The person SHALL approve the change; nothing implements before the person runs
`/opsx:apply <change>` (`$openspec-apply-change`). The only automated checks on a plan SHALL be
`openspec validate --strict` and the form of its `## Standard approach` section.

#### Scenario: Validator scope
- **WHEN** a change validates
- **THEN** no other script judges its content; the person does
