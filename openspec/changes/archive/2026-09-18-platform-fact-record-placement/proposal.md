## Why

The Codex review of PR 141 (`openspec/config.yaml:44`, `P2`) reads two texts of the same
rule against each other. The `proposal` rule of `config.yaml` (design D1 of the archived
change `observe-platform-facts`) puts the observation of a platform behaviour *before the
proposal is written* and its record *under **Why** or in design.md beside the decision*.
The requirement the archive wrote into `openspec/specs/planning/spec.md` says the
observation is recorded *before the design*, and its scenario says the proposal *or the
design* carries it *before the design exists* — a record in design.md cannot precede
design.md. The two texts part on when the record is made, and the architect-review
finding reads the rule, not the spec, so a plan could satisfy the one and violate the
other. Root cause: the spec delta named the time of the act (the observation precedes the
design) with the words of the record's place. The rule is right — the place of the record
is beside the decision, where its reader looks — and the spec is what changes.

## What Changes

- `planning`, "Platform facts are observed before a design rests on them": the
  observation is made before the proposal is written; its record sits under **Why** or in
  design.md beside the decision that rests on it. The scenario *Design on a platform
  behaviour* names the place, not a time before the design.
- No code, no rule text, no test: `config.yaml` already says this, and the tests read
  `config.yaml`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `planning`: "Platform facts are observed before a design rests on them".

## Impact

- Edited: `openspec/specs/planning/spec.md` (by the archive alone).
- Delivered on PR 141: the delta of a review fix, as the Deliver rule orders for a fix
  that changes a spec — no new issue, no new branch.
