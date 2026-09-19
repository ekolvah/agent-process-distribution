## MODIFIED Requirements

### Requirement: Architect review is the last step of the propose run
The `tasks` rule of `openspec/config.yaml` SHALL end the propose run with the architect
review: the `architect-reviewer` subagent in Claude, the planner as a self-review in Codex,
writes `openspec/changes/<change>/architect-review.md` (Verdict, Findings, Scenario coverage)
against `principles.md` §I–VII and the scenario → test map of `tasks.md`. The review contract
SHALL live in that rule, not in a schema: the schema is the unmodified `spec-driven`. On
`rework` the planner SHALL apply or answer every finding in the artifact it names and the
review SHALL run again. On `approve` the planner SHALL run `create_tracking_issue <change>`
— with the priority asked from the person when the change has no tracking issue yet — which
creates the issue from the proposal, sets its Status to `Planned` with the priority and
writes the number into `tasks.md`, or, when `tasks.md` already carries the number, sets
`Planned` alone and refuses a priority; the propose run ends there. The apply gate SHALL be
the first delivery task of `tasks.md` (the verdict line starts with `approve`), since
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

#### Scenario: Existing tracking issue
- **WHEN** `create_tracking_issue` runs on a change whose `tasks.md` already carries the issue number
- **THEN** it creates no issue, refuses a priority, and moves that issue to `Planned`

#### Scenario: Review archives with the change
- **WHEN** a change whose directory holds `architect-review.md` is archived
- **THEN** the file is in `openspec/changes/archive/<date>-<change>/` with the four artifacts
