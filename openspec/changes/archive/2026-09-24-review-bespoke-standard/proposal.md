## Why

The plan `v2-3-coverage-gate` (issue 113) passed the architect review with a bespoke
`check_coverage`: its own map format, its own parser and its own pytest run. The person's
solution review found it and parked it (issue 169). On 2026-09-24 the `bespoke` entry of
its `architect-review.json` read:

> check_coverage.py: no drift incident cited; it implements the check ADR 0027 decided
> ('coverage is a check', table row check_coverage, deletion condition recorded) …
> "result": "ok"

The cause is that `bespoke` is free text in
`skills/agent-process/architect-review.schema.json`: "the observed problem it closes
(issue, PR, run) or `none`".

- The validator accepts `none`, and it accepts an ADR decision in place of an observation.
  Yet `openspec/specs/planning/spec.md` makes a script without an observed problem a finding.
- Nothing asks for the established tool or standard for the job. For this job that is
  Gherkin with pytest-bdd, or traceability markers, and neither was weighed.

A clearer description would still be prose that the reviewer judges. The file is already
validated before any issue or branch exists (`create_tracking_issue`, `start_change`).
So the fix makes the evidence a structured field that this existing validator rejects.

## What Changes

- The review file gets a required `additions` list. It has one entry per script, check or
  non-test file the plan adds, with these fields:
  - `path`;
  - `problem`: an issue, PR or run reference;
  - `standard`: the established tool or standard for the job;
  - `why_not`: why that standard does not fit.
- Under `approve`, the schema rejects a `problem` that is not such a reference (`none`,
  "ADR 0027") and a `standard` of `none` or `n/a`. Under `rework`, the entry may record the
  gap honestly.
- The `bespoke` class judges the list: it is complete against Impact and the design, and each entry is true.
- The planning requirement states the list. ADR 0027 gets one Observations bullet.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `planning`: "Architect review is the last step of the propose run". It adds the
  `additions` list and the scenario "Addition without evidence".

## Impact

- Edited:
  - `skills/agent-process/architect-review.schema.json`
  - `tests/publisher/test_delivery_scripts.py`
  - `tests/publisher/test_planning_workflow.py`
  - `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`
- Added: none.
- Removed: none.
- No new script: validation is the existing `start_change.verdict`.
