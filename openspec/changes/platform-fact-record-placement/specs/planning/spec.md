## MODIFIED Requirements

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
