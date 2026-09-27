## Why

The backlog of this repository is now organised by an `Area` single-select field of Project 4
(one board view per area, order inside an area by position on the board), and the person no
longer uses `Priority`. The process still asks for a priority when it creates an issue and
never writes `Area`, so an issue it creates lands in no area view: the `Empty` view (filter
`-status:Done no:area`) exists only to catch them by hand (#219). Observed on 2026-09-27: after the field
was created, 1 of 20 open issues (#88) was not even a Project item, and every other issue had
to be assigned by hand.

Project 4 is also the template `init` copies (`gh project copy 4`, ADR 0027: the copy carries
every field, option and view), so a consumer's board now receives `Area` with this
repository's options and views.

## What Changes

- **BREAKING** `create_tracking_issue.py <change> --area <name>` replaces `--priority`; the
  area is required while the change has no tracking issue and refused once it has one.
- **BREAKING** `set_status.py <N> [<Status>] --area <name>` replaces `--priority`; the name
  resolves against the options of the Project's `Area` field (field drift is exit 2 listing
  the options, nothing written), as `--priority` does today.
- The "propose run not finished" hint of `start_change.py`, the architect-review step of
  `SKILL.md`, the issue rule of `.claude/rules/workflow.md` and the `context` of
  `openspec/config.yaml` ask for the area instead of the priority.
- `init` prints a third `manual` row: replace the template's `Area` options and area views
  with the consumer's own.
- The `Priority` field and its `high` view stay on Project 4 (and so on copies); the process
  no longer reads or writes it.

## Capabilities

### New Capabilities

### Modified Capabilities
- `state`: "Priority is set at creation" becomes "Area is set at creation"; the template
  Project carries an `Area` field.
- `distribution`: "Project UI actions are printed, not performed" prints the `Area` row too.
- `planning`: "A change is the unit of planning" and "Architect review is the last step of
  the propose run" name the area where they named the priority.
- `implementation`: "Delivery steps are tasks of every change" names the area where it named
  the priority.

## Impact

- Edited: `skills/agent-process/scripts/set_status.py`,
  `skills/agent-process/scripts/create_tracking_issue.py`,
  `skills/agent-process/scripts/start_change.py`, `skills/agent-process/scripts/init.py`,
  `skills/agent-process/SKILL.md`, `.claude/rules/workflow.md`, `openspec/config.yaml`,
  `tests/publisher/delivery_fakes.py`, `tests/publisher/test_set_status.py`,
  `tests/publisher/test_start_change.py`, `tests/publisher/test_planning_workflow.py`,
  `tests/publisher/test_init_remote.py`.
- Specs at archive: `openspec/specs/state/spec.md`, `openspec/specs/distribution/spec.md`,
  `openspec/specs/planning/spec.md`, `openspec/specs/implementation/spec.md`.
- Added / removed: none. ADR 0027 is not amended: its observation of what `gh project copy`
  carries is unchanged; the new field is recorded in the state spec.
- No consumer is installed yet (the person, 2026-09-27), so no board needs migrating; a board
  without `Area` would fail visibly (`no field 'Area'`, exit 2).
