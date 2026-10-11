## Why

Only sessions started through the launcher `.agent-process/scripts/task_session.py` send
traces: it sets the four trace variables in a `--settings` layer. The owner works in the
VS Code extension, which starts `claude` itself, so no session of the real workflow sends a
trace and Langfuse has nothing to analyse when Grafana shows that a task went wrong.

Observed on 2026-10-11 on the launched gate sessions of 2026-10-10 (Claude Code 2.1.296):

- **Langfuse groups spans by session.** Every span carries the attribute `session.id`, and
  Langfuse sets the observation's `sessionId` from it with no transform: observation
  `258697b8030e7db5` (`claude_code.llm_request`) has both equal to the session id. Each
  interaction is its own trace; the session groups them.
- **The events carry the tokens.** The Loki `api_request` event of the same request
  (`{service_name="claude-code"} | event_name="api_request"`, same `request_id`) carries
  `input_tokens` 2, `output_tokens` 3, `cache_read_tokens` 53729 and `cache_creation_tokens`
  54, equal to that observation's usage details.

A task's session ids are already in the archived change's `sessions` file
([ADR 0038](../../../.agent-process/docs/adr/0038-task-telemetry-follows-the-bound-sessions.md)),
so they find its traces in Langfuse with no tag, and the launcher's last job ("The launcher
stays") disappears once the trace variables are set where every session reads them.

Two gaps would remain. Alloy runs as a hand-started process (observed 2026-10-11: the
portable `%LOCALAPPDATA%/GrafanaAlloy/1.18.1/alloy.exe`, started by `run-alloy.ps1`, no
service), so a session after a reboot sends its spans nowhere. And the spans carry
`<REDACTED>` for every prompt and tool, so Langfuse shows timings and tokens that Grafana
already has, not what the agent did.

## What Changes

- Owner host: the four trace variables and the three content variables join the metrics and
  logs transport in the user-level settings `env`; the Alloy statement that tags spans by
  `task_id` is dropped and a statement masking token patterns is added; Alloy runs as an
  automatic Windows service, which replaces `run-alloy.ps1` and the portable binary.
- **BREAKING (owner tooling):** the launcher, its tests and its documentation are removed.
  The per-session token total moves from the cumulative counter to the `api_request` events,
  which a new process does not reset.
- ADR 0039 records the decision and supersedes the launcher parts of ADRs 0037 and 0038 and
  the "No content" part of ADR 0037.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true`: no spec names the launcher or the trace route; both are owner-side
measurement setup, which no consumer receives.

## Impact

- Removed: `.agent-process/scripts/task_session.py`, `tests/agent_process/test_task_session.py`.
- Added: `.agent-process/docs/adr/0039-every-session-sends-traces.md`.
- Edited: `.agent-process/docs/telemetry-measurement-setup.md`,
  `.agent-process/docs/adr/0037-one-emitter-feeds-both-telemetry-backends.md`,
  `.agent-process/docs/adr/0038-task-telemetry-follows-the-bound-sessions.md`.
- Owner host, outside the repository: `~/.claude/settings.json`, `~/.config/alloy/config.alloy`,
  the Alloy Windows service (installed), `run-alloy.ps1` and
  `%LOCALAPPDATA%/GrafanaAlloy` (removed).
