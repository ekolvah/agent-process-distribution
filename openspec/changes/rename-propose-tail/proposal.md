## Why

`create_tracking_issue` is the tail of the propose run: it checks release drift, validates
`architect-review.json` and its verdict, checks `## Standard approach` and binds the session
before it creates an issue or moves an existing one to `Planned`. The name describes only the
last step, so an agent can skip it when the issue already exists ("nothing to create") and a
reader looking for where a plan is checked does not look there. No skip has been observed; the
person raised the name while reviewing the standard-approach change.

## What Changes

- `skills/agent-process/scripts/create_tracking_issue.py` becomes `finish_propose.py`, its
  function `finish_propose`; `agent-process finish_propose` is the launcher command.
- No alias for the old name (design.md).
- The same rename in the callers, tests and current docs listed under Impact.

## Standard approach

- Renaming public functionality: [SemVer FAQ, "How should I handle deprecating
  functionality?"](https://semver.org/#how-should-i-handle-deprecating-functionality) — "there
  should be at least one minor release that contains the deprecation so that users can
  smoothly transition". It applies to a public API with callers outside the release; design.md
  records why the script name has none.
- Precedent in this repository: `finish_change.py` became `archive_change.py` without an alias
  (ADR 0027, the `v2-1d` entry), and `test_tasks_of_a_new_change` keeps `finish_change` in its
  list of names absent from the procedure.

## Capabilities

### New Capabilities

### Modified Capabilities
- `planning`: the propose tail is named `finish_propose` in "Architect review is the last step
  of the propose run" and "A change planned from an issue is tracked by it".
- `measurement`: the same name in "A session leads one task" and "The archive records the
  task's sessions".
- `distribution`: the same name in "Delivery entry scripts refuse release drift".

## Impact

- Renamed: `skills/agent-process/scripts/create_tracking_issue.py` → `finish_propose.py`.
- Edited: `skills/agent-process/SKILL.md`, `skills/agent-process/scripts/session_binding.py`,
  `skills/agent-process/scripts/start_change.py`, `tests/publisher/test_start_change.py`,
  `tests/publisher/test_session_binding.py`, `tests/publisher/test_plugin.py`,
  `tests/publisher/test_planning_workflow.py`,
  `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
  `.agent-process/docs/adr/0038-task-telemetry-follows-the-bound-sessions.md`,
  `.agent-process/docs/telemetry-measurement-setup.md`.
- Unchanged: `bin/agent-process`, which resolves any script by file name; archived changes and
  the history records of ADR 0027 (design.md).
