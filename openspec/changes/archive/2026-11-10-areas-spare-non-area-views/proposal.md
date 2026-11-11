## Why

The review of the `init-replaces-project-areas` PR found that `--area Bugs` took the template's
`Bugs` view by its name and replaced its filter: the step found a given area's view by name
alone, so a view that is not an area view was rewritten.

## What Changes

- A given area named after a view that is neither named after a template option nor carrying no
  filter or that area's filter leaves the linked Project `unchanged`, with the view named in
  the detail.
- The copy's views are read only when the step writes, so there the same view fails the step,
  naming it, before any write.

## Impact

- Edited: `skills/agent-process/scripts/project_areas.py`,
  `tests/publisher/test_init_remote.py`.
