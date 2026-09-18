## ADDED Requirements

### Requirement: Platform facts are observed before a design rests on them
A proposal whose design rests on a platform behaviour — an event, a permission, a merge
rule, a token scope, a CLI flag — SHALL record the observation of that behaviour before
the design: the reference page (its URL and the sentence) or the run id or command and its
output; a listing, a name or an inference SHALL NOT count. This is a `config.yaml` rule on
`proposal`. A platform behaviour a design rests on that is asserted without an observation
SHALL be an architect-review finding.

#### Scenario: Design on a platform behaviour
- **WHEN** the planner proposes a design that rests on a platform behaviour
- **THEN** the proposal or the design carries the observation — the reference page or the run id / command output — before the design exists

#### Scenario: Asserted platform fact
- **WHEN** a design rests on a platform behaviour and no observation stands beside it
- **THEN** the architect review reports it as a finding before the person approves
