## Why

The person orders work by an item's position on the board, not by a field: on 2026-10-14 the
open issues of Project 4 were ranked by moving them in the `Open` view, and the `Priority`
values left on three of them contradicted that order. The `state` spec still requires the
template to carry `Priority`, so every new consumer board is copied with a field nobody
writes. No script or view reads the field (`git grep -i priority` and the views' filters,
2026-10-14), and `init` copies the template only into a repository without a board
(`init.py`, step `project-copy`).

## What Changes

- The `state` requirement "The board is a copy of the template Project" closes the
  template's single-select fields to `Status` and `Area`, dropping `Priority`.
- The fake board of the tests drops its `Priority` field.
- The `Priority` field is deleted from Project 4.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `state`: requirement "The board is a copy of the template Project" — single-select fields
  are `Status` and `Area` only.

## Impact

- Edited: `openspec/specs/state/spec.md` (through the archive), `tests/publisher/delivery_fakes.py`.
- GitHub: the `Priority` field of Project 4 is deleted; consumer boards already installed are
  not touched.
