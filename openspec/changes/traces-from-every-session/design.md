## Context

The transport of metrics and logs, and why it sits in user settings rather than the process
environment, is in the setup document's
[What exports what](../../../.agent-process/docs/telemetry-measurement-setup.md#what-exports-what);
the Alloy pipeline is in
[Traces through Alloy to Langfuse](../../../.agent-process/docs/telemetry-measurement-setup.md#traces-through-alloy-to-langfuse).
The user settings `env` has no trace variable today.

## Goals / Non-Goals

**Non-Goals:**

- A Langfuse reading in `task_readings.py` or a link from the readings row to Langfuse.
- Trace export for adopters: telemetry stays owner-side
  ([ADR 0029](../../../.agent-process/docs/adr/0029-telemetry-leaves-the-v2-migration.md)).
- Routing metrics and logs through Alloy, or masking them: they stay direct (ADR 0037).

## Decisions

### D1. The trace variables live in the user-level settings `env`

The launcher's four trace variables move unchanged into the `env` block of
`~/.claude/settings.json`; the setup document keeps their one listing, moved from the
launcher block to the transport section. The signal-specific
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` overrides the shared Grafana endpoint for traces only:
the ADR 0037 gate sessions sent metrics to Grafana and traces to Alloy with both set; task
2.4 checks it again for an extension session.

This reverses ADR 0037's "Traces only for launched sessions": "User-scope trace variables
would send the spans of every session on the machine, other checkouts and consumer sandboxes
included, to this Langfuse project." The owner accepts that, unfiltered (decision of
2026-10-11): issue 396 asks for every session, as metrics and logs already do. Spans of
another repository stay apart by `resourceAttributes.vcs.repository.name` and by session id.

Volume: the Langfuse Hobby plan the owner uses "includes 50k units per month, 30-day data
access, and 2 users" ([pricing](https://langfuse.com/pricing)). The earlier launched and
plugin sessions gave about 2.5 observations per API request and 100–550 per session, so
about 1000 per task. The owner accepts the limit; reaching it is the reconsider condition,
and the owner's answer then is a self-hosted Langfuse, which has no unit limit (decision of
2026-10-11). The catcher is the usage page of the Langfuse organization.

Alternatives: an Alloy filter keeping only spans with `vcs.repository.name` (declined by the
owner); the project `.claude/settings.json` would send every clone's traces to a collector
only the owner's host runs; the VS Code extension's environment setting would miss CLI
sessions; the launcher misses every extension session, which is the problem.

### D2. Langfuse finds a task's traces by session id, without a tag

Langfuse sets `sessionId` from `session.id` (proposal). The owner opens each id of the
change's `sessions` file as a Langfuse session. The Alloy `langfuse.trace.tags` statement
reads `task_id`, which no resource carries once the launcher is gone, so it is removed. A tag
`session:<id>` would duplicate the native field.

### D3. The launcher is removed, and the per-session total reads the events

The readings read none of the launcher's resource attributes (ADR 0038). Its per-process
`service.instance.id` was a guard: it kept a resumed process on its own Grafana series, so the
per-session `max_over_time` of the cumulative token counter did not lose the earlier
process's tokens. Extension sessions never had it, and resumed extension sessions are routine.

- **What stops proving:** nothing that is kept. The documented per-session token total moves
  from the counter to the sum of the four token fields of the session's Loki `api_request`
  events (proposal), which no process restart resets, as the cost reading already does
  ([Per-task metrics](../../../.agent-process/docs/telemetry-measurement-setup.md#per-task-metrics)).
- **Effect:** the per-session comparison with Langfuse has one meaning again, a trace-schema
  change of the beta, instead of also flagging every resumed session.

### D4. Spans carry content, masked in the collector

`OTEL_LOG_USER_PROMPTS=1`, `OTEL_LOG_TOOL_DETAILS=1` and `OTEL_LOG_TOOL_CONTENT=1` join D1's
variables. This reverses ADR 0037's "No content": without content Langfuse shows only what
Grafana already has. Like D1 it applies to every session on the host, private repositories
included; the owner accepted that scope over a project-settings scope that would keep other
repositories redacted (decision of 2026-10-11). Per the
[monitoring reference](https://code.claude.com/docs/en/monitoring-usage), the first two also
fill log events (prompt and response text, tool input bounded to about 4K characters), so
Loki receives them; the third fills only spans (Bash output, Read text, MCP and web results),
each content attribute truncated at 60 KB.

The transform of `config.alloy` masks token shapes before export, in span attributes and span
event attributes:
`replace_all_patterns(attributes, "value", "(glc_|glsa_|sk-lf-|sk-ant-|gh[opsu]_|github_pat_)[A-Za-z0-9_+/=-]+", "<masked>")`.
Observed 2026-10-11 by prefix only, no value printed: the User-scope Grafana service-account
token starts with `glsa_`, and `~/.claude/.credentials.json` holds `sk-ant-` strings.
Tool output, where a printed environment or config file would surface a token, goes only to
traces and so passes the mask. Langfuse units count observations, not bytes, so the D1
volume stands.

### D5. Alloy runs as a Windows service

The Alloy Windows installer, run silently as Administrator with `/CONFIG` pointing at
`~/.config/alloy/config.alloy` and `/DISABLEREPORTING=yes`, registers an automatic service
under `LocalSystem` ([install on Windows](https://grafana.com/docs/alloy/latest/set-up/install/windows/)).
The Langfuse keys go into the service's `Environment` value under
`HKLM\Software\GrafanaLabs\Alloy`, copied from the User scope without printing; `sc.exe
failure` restarts it after a crash. The `logging { destination = "stderr" }` block of the
config goes, so the service logs to the Windows event log, its default. The default stability level is kept: every component of
the config is generally available, and `--stability.level=experimental` of `run-alloy.ps1`
was left from the Codex chain. `run-alloy.ps1` and the portable binary are removed.

A logon scheduled task running `run-alloy.ps1` would need no Administrator step and keep the
keys at User scope, but the script exits once it has spawned Alloy, so nothing restarts a
crashed Alloy and its output goes to files nobody reads; the service has both.

The route stays Claude Code → local collector → Langfuse, the OpenTelemetry
[agent pattern](https://opentelemetry.io/docs/collector/deploy/agent/). Alternatives:

- **Langfuse's Claude Code plugin** (a Stop hook rebuilding each turn from the transcript,
  the [integration](https://langfuse.com/integrations/developer-tools/claude-code) Langfuse
  recommends). Its script pins `langfuse>=4,<5` because it reaches SDK internals, exits
  silently on error, backdates timestamps instead of carrying Claude Code's span timings, and
  reads no subagent transcript; its cache usage keys were never checked against Langfuse
  prices. No plugin observation remains in Langfuse to compare (30-day retention).
- **Straight OTLP to Langfuse:** the spans carry no `gen_ai.usage.*`, so usage stays unmapped
  without the transform (ADR 0037), and nothing masks.

## Risks / Trade-offs

- **Alloy stopped.** Not yet observed: what the session shows when its trace export fails,
  and whether metrics and logs still arrive. Task 2.5 stops the service once and records the
  extension log lines and the Grafana series; ADR 0039 states the observed behaviour.
- **Content in Loki is not masked.** Prompts, responses and tool input of every repository,
  a token typed into a prompt or a Bash command line included, reach Grafana Cloud. The owner
  accepts it (D4).
- **Keys at machine scope.** The service reads the Langfuse keys from `HKLM`, readable by
  administrators of this single-user host.
- **Grafana headers on the trace export.** If the Grafana token of `otelHeadersHelper` reaches
  the trace exporter, it goes only to the loopback receiver. That receiver does not pass request
  metadata on: `include_metadata` is unset in `config.alloy`, and the
  [`otelcol.receiver.otlp` reference](https://grafana.com/docs/alloy/latest/reference/components/otelcol/otelcol.receiver.otlp/)
  gives its default as `false`; the exporter authenticates with its own `auth` block.
- **Beta schema.** ADR 0039's reconsider condition names the loss of `session.id` on spans.

Migration and rollback: the host edits are checked live before the repository removal (tasks
2.x before 3.x). Rollback: revert the PR, remove the seven variables, and restore the Alloy
config from the backup of 2.2; the service stays, since 2.6 removed the hand-start script.
