## Why

An adopter that did every `manual` row `init` printed still gets empty task readings: the
adopter `ekolvah/lampa-mediacenter` (installed at v3.29.0) ended three task-readings runs
(its PRs 41, 45, 46) red, every row with empty `start` / `hours` / `agent_hours` / cost /
counts and `telemetry: no token sample of <session_id>`. The sessions' series are in
Prometheus (`claude_code_token_usage_tokens_total{session_id=~"..."}` returns all three), but
no series of that stack carries `vcs_repository_name`, so `_START_QUERY` of
`.agent-process/scripts/task_readings.py`, filtered on `vcs_repository_name="<owner>/<repo>"`,
matches nothing (observation of issue 475; adopter fix ekolvah/lampa-mediacenter#49).

**Root cause:** the adopter's `.claude/settings.json` has no `env.OTEL_RESOURCE_ATTRIBUTES`.
`telemetry-measurement-setup.md` ("Which label carries the project", "Adopters") says the
adopter sets it by hand, but neither `init`'s `settings` step nor any `manual` row of
`skills/agent-process/scripts/manual.py` sets, names or checks it, so an adopter learns of the
step only when the readings come out empty — a "must not forget X" kept in prose. Series
written before the value is set carry no label and cannot be recovered.

**Reproduction:** a confirmed run of `init` on a consumer without the value leaves
`.claude/settings.json` without `env.OTEL_RESOURCE_ATTRIBUTES` and prints no row naming it
(the RED tests of this change).

## What Changes

- `init`'s `settings` step writes `env.OTEL_RESOURCE_ATTRIBUTES` =
  `vcs.repository.name=<owner/repo>,vcs.repository.url.full=https://github.com/<owner/repo>`
  into the consumer's `.claude/settings.json` when nothing would be lost: the file is absent,
  or is in the form `init` writes and sets no such variable, and this machine sets no value of
  that variable.
- Otherwise, while the file's value does not name the repository, a run prints a
  `manual telemetry-attribution` row with the value and the reason `init` did not write it.
- `telemetry-measurement-setup.md` drops "by hand" for the adopter's attribution.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: a new requirement *Init writes the telemetry attribution*, and *Manual rows
  follow observed state* counts the attribution in its "Observed done" and "Unreadable state"
  scenarios.

## Impact

- Edited: `skills/agent-process/scripts/manual.py` (the attribution state, the row, the
  settings form `json_text` moved here from `init.py`).
- Edited: `skills/agent-process/scripts/init.py` (the `settings` step writes the value).
- Edited: `tests/publisher/conftest.py` (an autouse fixture clears `OTEL_RESOURCE_ATTRIBUTES`),
  `tests/publisher/test_init_remote.py` (the scenarios), `tests/publisher/test_init_config.py`
  (a done file in another form prints no row).
- Edited: `openspec/specs/distribution/spec.md` (by archive).
- Doc-only: `.agent-process/docs/telemetry-measurement-setup.md` ("Which label carries the
  project", "Adopters").
- No dependency, workflow or template change.
