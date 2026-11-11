## Why

`init` prints `manual project-visibility: <Project>/settings -- a copy is private; set its
visibility as intended` whenever the linked Project is not public
(`skills/agent-process/scripts/manual.py:106`). The row is observed done only at `public: true`,
so a person who keeps the board private on purpose sees it on every run and cannot dismiss it.

Root cause: the row treats public as the target state, but nothing in the process needs the
consumer's copy public. Observed:

- Only the template must be public, so that `gh project copy` can read it for a consumer under
  another owner — on record in `openspec/changes/archive/2026-09-16-v2-2a-board-template/design.md:10`;
  the template requirement (`openspec/specs/state/spec.md:34`) is unchanged.
- `set_status` and `manual` read the linked Project with the owner's token, and no workflow
  reads a Project: `grep -rn "projectV2\|project " .github/workflows/*.yml` prints nothing.
- The query's `public` field is read only by this row (`manual.py:327`).

Reproduction: `tests/publisher/test_init_remote.py::test_manual_actions_are_printed` asserts the
row for a private copy today.

## What Changes

- `init` no longer reads the linked Project's visibility and prints no `project-visibility` row.
- The "Observed done" scenario no longer requires a public Project.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: "Project UI actions are printed, not performed" drops the visibility row;
  "Manual rows follow observed state" drops "public" from "Observed done".

## Impact

Edited: `skills/agent-process/scripts/manual.py`, `skills/agent-process/scripts/init.py`
(docstring), `tests/publisher/test_init_remote.py`, `tests/publisher/init_harness.py`, and
`openspec/specs/distribution/spec.md` through the archive.

Not edited: ADR 0027 (line 287) records what v2-2a decided at the time; this change's archived
design records the later decision.
