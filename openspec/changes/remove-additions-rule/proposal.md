## Why

Reproduction (issue 186; `ekolvah/agent-process-sandbox` issue 117, step 7a): a first ordinary feature
(`add-smoke-test-script`: `smoke.py` and its test) was proposed with no prior issue. Under
`approve`, `architect-review.schema.json` requires each `additions` entry — every "script, check
or non-test file" — to cite an issue, PR or run as `problem`; the tracking issue is created only
after `approve`, so the reviewer cited the unrelated install PR `#1` to validate.

Root cause: the guard against bespoke additions is itself bespoke — a regex on a reference
format, not a judgement of relevance, and scoped to every non-test file, so ordinary product
code falls under it. The industry form of this guard is a decision record with the alternatives
considered (MADR "Considered Options", Rust RFC "Rationale and alternatives", OpenSpec
`design.md` Decisions) judged by a reviewer; the research is in the thread of issue 186. This plan keeps
that form: the justification of a new script or check lives in `design.md`, the `bespoke` class
of the review judges it.

## What Changes

- **BREAKING** (review file format): `architect-review.schema.json` loses the `additions`
  property, its `required` entry and its `approve` constraint; a review file that still carries
  `additions` fails validation as an additional property.
- The `bespoke` class judges each script or check the plan adds (not every non-test file)
  against the `design.md` decision beside it: the problem it closes and the standard for its job
  and why it does not fit; an issue, PR or run is cited when one exists.
- The Design procedure of `SKILL.md` asks for that decision.
- ADR 0027 records the decision.

## Capabilities

### New Capabilities

### Modified Capabilities
- `planning`: "Architect review is the last step of the propose run" drops the `additions`
  sentence; its scenario "Addition without evidence" now refuses a review carrying the key
  (design D1); the `bespoke` finding class reads the design decision; "Plan without a prior
  issue" is added.

## Impact

- Edited: `skills/agent-process/architect-review.schema.json`, `skills/agent-process/SKILL.md`
  (Design), `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
  `tests/publisher/test_start_change.py`, `tests/publisher/test_planning_workflow.py`,
  `openspec/specs/planning/spec.md` (at archive).
- Added, removed: none.
- Consumers: an in-flight `architect-review.json` with `additions` is rejected by
  `create_tracking_issue` / `start_change` naming the property; the reviewer rewrites it without
  the key.
