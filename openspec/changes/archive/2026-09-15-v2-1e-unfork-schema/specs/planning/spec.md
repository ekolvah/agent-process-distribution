## ADDED Requirements

### Requirement: Architect review is the last step of the propose run
The `tasks` rule of `openspec/config.yaml` SHALL end the propose run with the architect
review: the `architect-reviewer` subagent in Claude, the planner as a self-review in Codex,
writes `openspec/changes/<change>/architect-review.md` (Verdict, Findings, Scenario coverage)
against `principles.md` §I–VII and the scenario → test map of `tasks.md`. The review contract
SHALL live in that rule, not in a schema: the schema is the unmodified `spec-driven`. On
`rework` the planner SHALL apply or answer every finding in the artifact it names and the
review SHALL run again; the propose run ends on `approve`. The apply gate SHALL be the first
delivery task of `tasks.md` (the verdict line starts with `approve`), since artifact status is
file existence only.

#### Scenario: Review finding
- **WHEN** the review finds a simpler design or a scenario missing from the map
- **THEN** the finding is in `architect-review.md` before the person approves

#### Scenario: Rework verdict
- **WHEN** `architect-review.md` says `rework`
- **THEN** the propose run applies or answers the findings and reviews again, and no
  delivery task runs until the verdict is `approve`

#### Scenario: Review archives with the change
- **WHEN** a change whose directory holds `architect-review.md` is archived
- **THEN** the file is in `openspec/changes/archive/<date>-<change>/` with the four artifacts

## REMOVED Requirements

### Requirement: Architect review is an artifact of the change
**Reason**: The review was a fifth artifact of a forked schema; `openspec schema` is
experimental in 1.13.0 and a fork cannot follow upstream. The same gate is now a rule on
`spec-driven` and the first delivery task.
**Migration**: The review is invoked by the `tasks` rule as the last step of the propose run
("Architect review is the last step of the propose run"); `openspec/schemas/` is removed and
`schema: spec-driven` is set in `openspec/config.yaml`. Existing archived changes keep their
`architect-review.md` as it is.
