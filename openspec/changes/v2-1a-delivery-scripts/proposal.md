## Why

The OpenSpec apply loop needs four deterministic steps that v1 has no script for: set the
Project status and priority of a tracking issue in one call, prove RED from the runner's own
report, wait for a PR's checks and review threads, and archive a change inside its PR.
Without them the delivery tasks of every `tasks.md` stay prose an agent may skip.

This is the first of three changes that replace `v2-1-planning-workflow` (tracking issue
#111); the pre-split change directory is removed here. The other two: the planning schema
and rules (`v2-1b-planning-schema`), the removal of the v1 planner (`v2-1c-remove-v1-planner`).

## What Changes

- `.agent-process/scripts/set_status.py <N> "<Status>" [--priority <name>]`: Project item,
  fields and options resolved by name; unknown option or unresolvable Project → exit 2,
  nothing changed.
- `.agent-process/scripts/wait_for_pr.py <PR>`: blocks until every check on the head has
  concluded on two consecutive polls, then prints failed checks and unresolved threads;
  exit 0/1/3.
- `.agent-process/scripts/finish_change.py <change>`: marks its own task, archives, removes
  the lock a successful archive leaves, commits, pushes, re-requests the Codex review, waits.
- `check_red.py --report <junit.xml> <node ids>`: reads the declared runner's report, spawns
  nothing; the v1 CLI stays. `AGENTS.md` declares the runner command and report path.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `implementation`: RED first from the runner's report; delivery steps are tasks of every
  change; the implementing run ends only after checks and reviews.
- `state`: priority is set when the tracking issue is created.

## Impact

- Added: the three scripts, `tests/publisher/test_delivery_scripts.py`, `.gitignore` entry
  for the report.
- Edited: `check_red.py`, `AGENTS.md` (runner bullet).
- Removed: `openspec/changes/v2-1-planning-workflow/` (pre-split plan; superseded by the
  three changes).
- Kept until v2-4: `set_issue_status.py`, `set_issue_priority.py`, `request_codex_review.py`.
- No `config.yaml` rule refers to the scripts yet; `v2-1b-planning-schema` adds the `tasks`
  rule that puts them into every `tasks.md`.
