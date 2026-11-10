## Why

`init` prints `manual project-areas` while the linked Project's `Area` options equal the
template's (`skills/agent-process/scripts/manual.py:110`): the person replaces the options and
the area views in the UI. Tracking issue 493 asks for an `init` transition, now that the
Projects v2 API covers both, and first for a source of the consumer's areas, which `init` has
none of today. The person chose a repeatable `--area <name>` (2026-11-10).

Observations (gh 2.87.3, 2026-11-10, on a scratch copy of template Project 4 made with the
person's token and deleted after):

- The copy carries the template's views — `Open`, `Bugs`, `Empty` and one `BOARD_LAYOUT` view
  per option named after it, e.g. `Distribution | -status:Done area:"Distribution"` — and its
  five `Area` options.
- `updateProjectV2Field(singleSelectOptions:[{name:"Alpha",…},{name:"Beta Two",…}])` left
  exactly those two options.
- `createProjectV2View(name:"Alpha", layout:BOARD_LAYOUT)` made a view with `filter: null`;
  `updateProjectV2View(viewId, filter:"-status:Done area:\"Alpha\"")` set it;
  `deleteProjectV2View(viewId)` removed `Distribution`.
- On a second scratch copy, `updateProjectV2View(viewId, name:"Alpha", filter:…)` renamed
  `Distribution` and kept its fields (`Labels`, `Area` among them) and Status columns; a view
  made by `createProjectV2View` shows neither `Labels` nor `Area`.
- `gh project copy` under the agent identity `ekolvah-agent` failed: "does not have the correct
  permissions to execute `CopyProjectV2`".

## What Changes

- `init` takes a repeatable `--area <name>`; an empty name, a name holding `"`, or a repeated
  name exits 2.
- A new transition `project-areas`, after `pre-push`: with `--area`, while the linked
  Project's `Area` options are the template's, it makes the area views and then the options
  exactly the given names; a retry with the same names completes a failed run.
- The `manual project-areas` row names `--area` for the template's options, and is no longer printed when the linked
  Project is the template itself.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: *Init's remote writes are the Project and the installation PR* and *Project
  UI actions are printed, not performed* admit the areas transition; added *Init replaces the
  template's areas*.

## Standard approach

GitHub's GraphQL Projects reference (https://docs.github.com/en/graphql/reference/projects) and
the REST Project views reference (https://docs.github.com/en/rest/projects/views); design D3.

## Impact

- Edited: `skills/agent-process/scripts/init.py` (flag, step, docstring),
  `skills/agent-process/scripts/manual.py` (the shared areas read, row text),
  `skills/agent-process/SKILL.md` (Install step 2), `commands/init.md` (argument hint),
  `tests/publisher/init_harness.py` (the fake Project's views and mutations),
  `tests/publisher/test_init_remote.py`.
- No ADR: the one decision with alternatives (design D1) is a one-time input whose record is
  this change's design.
- Remote: none at install of this change; a consumer's Project on its next `init --area`.
