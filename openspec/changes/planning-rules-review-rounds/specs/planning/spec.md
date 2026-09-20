## ADDED Requirements

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
