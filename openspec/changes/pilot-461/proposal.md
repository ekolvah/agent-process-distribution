## Why

Planning reads documentation only to verify facts a finished design rests on: `platform` checks
that the platform behaves as assumed, `bespoke` asks for a standard only for an added script or
check. Nothing asks, before designing, how the vendor recommends using an external tool and what
the industry-standard approach to the problem is. Observed in #177: the model's facts were
verified from its docs, but the first prefilter measurement (v1) was designed ad hoc; the
vendor's usage recommendations were applied only in a second run (v2), and the standard approach
(model cascades / routing) was not cited with a source.

## What Changes

- `skills/agent-process/SKILL.md` § Proposal opens with a step: read the usage guidance of each
  external tool, model or API the task touches, and record the industry-standard approach with
  its source under `## Standard approach` in `design.md` or `proposal.md`.
- `create_tracking_issue` refuses a plan whose section is missing or out of form (spec planning).
- The architect-review class `bespoke` judges the content for every plan.

## Capabilities

### New Capabilities

### Modified Capabilities
- `planning`: new requirement "Planning starts from the standard approach"; "Architect review is
  the last step of the propose run" adds the section to the refusals of `create_tracking_issue`;
  "Human approval is the gate" admits the form check of that section beside `openspec validate --strict`.

## Impact

- Edited: `skills/agent-process/SKILL.md`, `skills/agent-process/scripts/create_tracking_issue.py`,
  `skills/agent-process/architect-review.schema.json`, `tests/publisher/delivery_fakes.py`,
  `tests/publisher/test_start_change.py`, `tests/publisher/test_planning_workflow.py`,
  `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`.
- Added: none. Removed: none.
