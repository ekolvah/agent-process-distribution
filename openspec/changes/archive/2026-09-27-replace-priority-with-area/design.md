## Context

`set_status.py` resolves every field and option by name from `gh project field-list` before
any write; `create_tracking_issue.py` restricts `--priority` with argparse `choices`
(`High|Medium|Low`), creates the issue, writes its number into `tasks.md`, and only then calls
`set_status`. Project 4 is both this repository's board and the template `init` copies.

## Goals / Non-Goals

**Goals:** the process writes `Area` wherever it wrote `Priority`, and a wrong area name
never leaves a created issue behind.

**Non-Goals:** deleting `Priority` or its `high` view (the person keeps them for manual use);
a separate template Project; creating the `Area` field on an already installed consumer board;
ordering items on the board (position stays manual).

## Decisions

**D1 — `--area` replaces `--priority` one for one.** `set_status(number, status, *, area)`
writes `fields["Area"]` through the existing `_option_id`; `--priority` is removed, not kept
as an alias, because nothing should write the field the person stopped using. Alternative:
accept both — rejected: two creation fields are the drift this change removes (#219).

**D2 — area names come from the Project, checked before the create.** Areas are
per-repository, so `create_tracking_issue` has no `choices` list. This replaces a
project-declared input (the fixed `PRIORITIES`) with one the caller supplies:
- Failure modes: a typo, an area the board lacks, a board with no `Area` field (a consumer
  installed before this change).
- What stops proving: argparse no longer rejects a bad name before `gh issue create`.
- Catcher: `set_status.check_area(area, gh)` (the same `_repo` → `_linked_project` → `_fields`
  read, no write) is called by `create_tracking_issue` right after the verdict check and
  before `gh issue create`; an unknown name or missing field is exit 2 naming the options or
  fields, and no issue exists. Proven by the `Area field drift` test on the create branch
  (fake `gh` records no `issue create`). `set_status` itself keeps its resolve-before-write
  order for the `Area only` path.

**D3 — the existing-issue branch refuses `--area`,** as it refused `--priority`: the area was
set at creation (for #219 by hand, on 2026-09-27).

**D4 — the template's areas are a `manual` row.** `gh project copy` carries this repository's
`Area` options and views to every consumer (ADR 0027 observation). `init` adds
`manual project-areas: <url>/settings -- replace the Area options and the area views with
this repository's own`; it issues no field or view mutation, keeping init's only GitHub
writes the copy and the link. Alternative: a separate template Project — rejected by the
person (one board).

## Risks / Trade-offs

- [A board without an `Area` field] → the propose tail exits 2 with
  `no field 'Area' in the Project; fields: …` before creating the issue (D2); the person adds
  the field. No silent fallback to `Priority`. No consumer is installed yet (the person,
  2026-09-27), so no board is affected today.
- [This repository's areas leak into a consumer's board] → the D4 row names it; the person
  edits the copy.

## Migration Plan

Merging the PR switches the scripts; Project 4 already has `Area` (created 2026-09-27).
Rollback is reverting the PR: `Priority` is still on the board, so the old calls work again.
