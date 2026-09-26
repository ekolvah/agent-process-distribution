## Why

One process release applies per machine: the publisher bumps the release, the machine updates
the Claude plugin (`/plugin marketplace update`) or the user-wide Codex link, and each consumer
catches up by re-running Install. Between those steps a consumer and the loaded skill disagree
on the release and nothing detects it: old scripts run against a project installed by a newer
release, or the reverse, and the failure surfaces downstream (CI, statuses, review) far from its
cause (#190, split out of #187).

Root cause: the consumer records no release. `init.py` renders the release into the managed
workflow only (`render_workflow(version, …)`, observed in `skills/agent-process/scripts/init.py`),
and the `openspec/config.yaml` block carries the OpenSpec pin alone
(`skills/agent-process/templates/config.yaml`), so no script can compare what the project was
installed with against its own `VERSION`. The first delivery commands a carrier runs are
`create_tracking_issue.py` (end of propose) and `start_change.py` (Group 0); neither reads a
release today.

`## Install` no longer claims a per-repository plugin pin: #191 replaced it with the #184
observation, so this change leaves that text alone.

## What Changes

- The installer records `# agent-process release: <version>` in its `openspec/config.yaml` block.
- `start_change.py` and `create_tracking_issue.py` compare it with the skill's `VERSION` before
  any other step and exit 2 when it is absent, unparsable or different, naming both releases and
  the fix: re-run Install with this skill (project behind or not recorded), or update the plugin
  or the Codex link and restart the session (skill behind). They never update the skill
  themselves (decided with the person: a plugin or link update is machine-wide and the session
  needs a restart anyway).
- Only the publisher's own checkout, `<root>/skills/agent-process/scripts`, is exempt; a copy of
  the scripts anywhere else is compared.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the config block records the installed release, and the delivery entry scripts refuse a release that differs from the skill's.

## Impact

- Edited: `skills/agent-process/templates/config.yaml`, `skills/agent-process/scripts/init.py`,
  `skills/agent-process/scripts/start_change.py`,
  `skills/agent-process/scripts/create_tracking_issue.py`, `tests/publisher/test_init.py`,
  `tests/publisher/test_delivery_scripts.py`.
- Added: none. Removed: none. No doc edit: the exit messages carry the fix, and `## Install`
  already names the plugin update (#191).
- Consumers installed by 2.0.0 have no recorded release: their first `create_tracking_issue` or
  `start_change` after this release exits 2 asking to re-run Install, which writes the line.
