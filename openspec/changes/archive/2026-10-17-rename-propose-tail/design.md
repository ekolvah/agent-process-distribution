## Context

Consumers reach the propose tail as `agent-process create_tracking_issue`; the agent learns the
command from `SKILL.md` and from `start_change`'s `propose run not finished` message.

## Goals / Non-Goals

**Goals:** the script and its function are named after their role wherever the process is read
today: specs, `SKILL.md`, scripts, tests, current docs.

**Non-Goals:** any behaviour change of the tail or of `start_change`.

## Decisions

### The name is `finish_propose`

It names the role (the end of the propose run), pairs with `start_change` and `archive_change`
as a verb-object command, and answers `start_change`'s own message, `propose run not
finished`. Rejected: `plan_ready` reads as a predicate, not a step that creates an issue and
moves its Status.

### No alias for the old name

The SemVer deprecation window protects callers outside the release. The script name has none:
`SKILL.md` and `start_change`'s `NOT_FINISHED`, which prints the script's path, ship in the
same plugin release as the script, and the tail and `start_change` refuse a skill whose release
differs from the project's ("Delivery entry scripts refuse release drift"). A plugin update
takes a session restart, after which the agent reads the new `SKILL.md`. A stale call from text
outside the plugin fails visibly: the launcher exits 2 listing the scripts, `finish_propose`
among them (`test_launcher_refuses_an_unknown_script`). An alias would be a second entry point
to keep, test and later delete (§VII).

### Which documents change

Current descriptions change: the deletion condition of ADR 0027 (a live trigger), ADR 0038's
"Chosen" binding list, `telemetry-measurement-setup.md`. The dated entries and the script table
of ADR 0027 are history records and stay; a new dated entry records this rename and the
no-alias decision.

### The old name is a guarded absence

`test_tasks_of_a_new_change` lists names that must not reappear in the procedure
(`finish_change` among them); `create_tracking_issue` joins it. It fails on today's `SKILL.md`,
so it is the RED of this change and a lasting guard. The scenario titles do not change, so the
other tests keep their names and change only the script name they load or assert.

## Risks / Trade-offs

- [A person's note or memory names the old command] → exit 2 with the script list, as above.

## Migration Plan

One PR; rollback is its revert.
