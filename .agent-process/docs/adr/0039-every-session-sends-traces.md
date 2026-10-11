---
status: "accepted"
date: 2026-10-11
decision-makers: ekolvah
---

# Every session sends traces

## Context and Problem Statement

[ADR 0037](0037-one-emitter-feeds-both-telemetry-backends.md) sends traces only from sessions
started through the launcher `task_session.py`, and
[ADR 0038](0038-task-telemetry-follows-the-bound-sessions.md) keeps the launcher for that
alone. The owner works in the VS Code extension, which starts `claude` itself, so no session
of the real workflow sent a trace. Langfuse had nothing to analyse when Grafana showed that a
task went wrong.

Observed on 2026-10-11 on the launched gate sessions (Claude Code 2.1.296):

* every span carries `session.id`, and Langfuse sets the observation's `sessionId` from it
  with no transform; each interaction is its own trace, and the session groups them;
* the Loki `api_request` event of a request carries `input_tokens`, `output_tokens`,
  `cache_read_tokens` and `cache_creation_tokens`, equal to the usage details of the same
  request's Langfuse observation.

Two more gaps: Alloy ran as a hand-started portable binary, so after a reboot the spans went
nowhere, and the spans carried `<REDACTED>` for every prompt and tool, so Langfuse showed only
the timings and tokens that Grafana already has.

## Considered Options

* **Trace scope:** the launched session only (ADR 0037); every session on the host, from the
  user-level settings; every session, filtered in Alloy to spans with `vcs.repository.name`;
  the project `.claude/settings.json`; the VS Code extension's environment setting.
* **Content:** none, prompts as `<REDACTED>` (ADR 0037); prompts, tool details and tool output,
  masked for token shapes in the collector; the same, from project settings only.
* **Route:** Claude Code → local Alloy → Langfuse; Langfuse's Claude Code plugin; straight
  OTLP to Langfuse.
* **Alloy process:** a Windows service; a logon scheduled task running `run-alloy.ps1`.

## Decision Outcome

Chosen: **every session on the owner's host sends traces with content through an Alloy
Windows service that masks token shapes; a task's traces are the Langfuse sessions of its
bound session ids; the launcher is removed.** The variable listing and the Alloy pipeline
are in the [setup document](../telemetry-measurement-setup.md).

* **D1. User settings.** The four trace variables join the metrics and logs transport in the
  `env` of `~/.claude/settings.json`. `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` overrides the shared
  Grafana endpoint for traces only. The scope is unfiltered: other checkouts and consumer
  sandboxes on the host send spans too, apart by `vcs.repository.name` and session id. The
  project settings would send every clone's traces to a collector only the owner runs; the
  extension's environment setting misses CLI sessions.
* **D2. Session id, no tag.** A task's traces are the Langfuse sessions of the ids in its
  archived `sessions` file. The `langfuse.trace.tags` statement read `task_id`, which no
  resource carries any more, and is removed.
* **D3. The launcher goes.** The readings read none of its attributes (ADR 0038). Its
  per-process `service.instance.id` kept a resumed process on its own counter series;
  extension sessions never had it. The per-session token total reads the `api_request`
  events instead, which no process restart resets.
* **D4. Content, masked.** `OTEL_LOG_USER_PROMPTS=1`, `OTEL_LOG_TOOL_DETAILS=1` and
  `OTEL_LOG_TOOL_CONTENT=1` join D1, for every repository on the host. The Alloy transform
  replaces `(glc_|glsa_|sk-lf-|sk-ant-|gh[opsu]_|github_pat_)[A-Za-z0-9_+/=-]+` with `<masked>`
  in span and span event attributes. Tool output arrives as the span event `tool.output`,
  which Langfuse drops: its OTLP ingestion reads span events only under `gen_ai.*` names. After
  the mask, the transform copies the event's `output`, `content` or `diff` into the span's
  `langfuse.observation.output`. Model responses stay out of Langfuse: they come only with
  detailed beta tracing, whose endpoint takes logs off their exporter too, against ADR 0037's
  direct route. Loki receives prompts, responses and tool input unmasked; the owner accepts it.
* **D5. Alloy service.** The silent installer, with `/CONFIG` at `~/.config/alloy/config.alloy`
  and `/DISABLEREPORTING=yes`, registers an automatic `LocalSystem` service. The Langfuse keys
  sit in its `Environment` value under `HKLM\Software\GrafanaLabs\Alloy`, `sc.exe failure`
  restarts it, and it logs to the Windows event log. `run-alloy.ps1` and the portable binary
  are removed. A logon task would keep the keys at User scope, but nothing would restart a
  crashed Alloy. The plugin pins SDK internals, exits silently on error, backdates
  timestamps and reads no subagent transcript. Straight export leaves usage unmapped and
  nothing masks.

### Readings

Extension sessions, 2026-10-11, Claude Code 2.1.296, a prompt that ran
`echo glc_MASKPROBE0000` and one subagent:

* the spans carry `langfuse.observation.usage_details` and no `langfuse.trace.tags`;
* the interaction span carries the prompt text;
* the probe appears only as `<masked>`: in the prompt, in `full_command`, and as the Bash
  observation's output;
* Write and Read observations carry the file text as output, Edit the structured diff;
* a failed call (Read of a missing file, Bash with a non-zero exit) has no `tool.output` event
  and no output; Glob, Agent and the subagent handback have none either;
* the subagent's spans are in the session;
* the Loki `api_request` token sums of the session equal the Langfuse usage per type.

Alloy unreachable, 2026-10-11: the receiver was moved off `127.0.0.1:4318` by a config reload,
which refuses the connection as a stopped service does, and one headless session ran. It
completed normally. Its debug log had one line,
`[3P telemetry] First traces export: FAILED (connect ECONNREFUSED 127.0.0.1:4318)`, and
nothing reached stderr. Its Grafana token series and Loki events arrived. Its spans never
reached Langfuse: the exporter does not retry them once Alloy is back.

### Consequences

* Good, because every session of the real workflow is in Langfuse, found by the session ids
  the readings already use.
* Good, because Langfuse shows what the agent did: prompts, tool input and tool output.
* Good, because the per-session token total no longer loses a resumed process's tokens.
* Bad, because a token outside the masked shapes reaches Langfuse, and every content field
  reaches Loki unmasked.
* Bad, because spans exported while Alloy is down are lost, with one debug-log line as the
  only sign. Metrics and logs are unaffected.
* Bad, because every session on the host counts against the Langfuse Hobby limit of 50k units
  a month.
* Neutral: the service reads the Langfuse keys from `HKLM`, which every local account can
  read; on this single-user host that is the reach of the User-scope copy.

### Reconsider condition

* Spans lose `session.id`, Langfuse stops mapping it to `sessionId`, or `api_request` loses its
  token fields.
* The Langfuse unit limit is reached; the owner's answer then is a self-hosted Langfuse.
* A token is found unmasked in Langfuse.
* Langfuse reads the `tool.output` event itself, or Claude Code emits model responses without
  rerouting logs.

### Confirmation

The readings above were taken live, because both ingest paths are third-party. The setup
document carries no launcher, `task_id` or tag reference, checked by `git grep`.
