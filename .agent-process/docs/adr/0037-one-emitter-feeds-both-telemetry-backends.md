---
status: "accepted"
date: 2026-10-10
decision-makers: ekolvah
---

# One emitter feeds both telemetry backends

## Context and Problem Statement

[ADR 0036](0036-per-task-token-analysis-backend.md) keeps per-task totals on Grafana and
names the next step: Claude Code's own OpenTelemetry export, traces beta included, feeds
both Grafana and Langfuse, with the task identity as a resource attribute. The Langfuse
plugin, a second emitter, could not agree with it on totals.

Two observations set the shape:

* **The process environment cannot carry the task.** The project's `.claude/settings.json`
  sets `OTEL_RESOURCE_ATTRIBUTES`, and a settings value replaces the process value
  ([ADR 0026](0026-project-attribution-rides-the-telemetry-resource-attributes.md),
  observed). A probe with `task_id=probe-101` in the environment of Claude Code 2.1.295
  exported spans without it.
* **The trace spans carry the usage.** The same probe exported, with
  `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, the spans `claude_code.interaction`,
  `claude_code.llm_request`, `claude_code.tool`, `claude_code.tool.execution` and
  `claude_code.tool.blocked_on_user`. `claude_code.llm_request` carries `input_tokens`,
  `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `gen_ai.request.model`
  and `session.id`. It carries no `gen_ai.usage.*` attribute.

## Considered Options

* **Task identity:** a hand-typed `claude --settings '<json>'`; editing
  `.claude/settings.local.json`; an owner launcher that composes the `--settings` layer.
* **Trace route:** Claude Code straight to Langfuse's OTLP endpoint; through the local
  Alloy collector.
* **Trace scope:** host-wide User-scope trace variables; the launched session only.

## Decision Outcome

Chosen: **an owner launcher composes the identity, and launched sessions send traces
through Alloy to Langfuse. Metrics and logs stay on their direct route to Grafana.**

* **Launcher.** `python .agent-process/scripts/task_session.py --issue N [--attempt K] --
  claude …` inserts one `--settings` JSON after the executable. Its `env` holds the project's
  `OTEL_RESOURCE_ATTRIBUTES` plus `task_id=issue-N,attempt_id=K,service.instance.id=<uuid4>`
  and the four trace variables: `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`,
  `OTEL_TRACES_EXPORTER=otlp`, `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:4318/v1/traces`
  and `OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf`. Hand-typing repeats the project pairs
  on every launch and needs different quoting in PowerShell and Git Bash. The local settings
  file is shared by parallel sessions of one checkout and outlives the session.
* **A process per series.** A resumed session is a new process whose cumulative counters
  restart from zero. Without a per-process attribute it writes to the series of the previous
  process, and the reset hides that process's tokens: the first gate run lost two of three
  processes. `service.instance.id` becomes the label `instance`; `job` stays
  `claude-code` (observed). ADR 0026 rejected this attribute as the *project* carrier
  because it would orphan accumulated series. Here every series is already split by
  `session_id`, so no series continues across launches and nothing is orphaned.
* **Alloy.** One receiver, `otelcol.receiver.otlp "claude_code"` on `127.0.0.1:4318`, with a
  `traces` output only, feeds `otelcol.processor.transform` → `otelcol.processor.batch` →
  `otelcol.exporter.otlphttp` to `https://cloud.langfuse.com/api/public/otel`. Basic auth
  takes the Langfuse keys from `sys.env`, and the exporter sends the header
  `x-langfuse-ingestion-version: 4`. The transform sets two span attributes:
  * `langfuse.observation.usage_details`, a `Concat` JSON
    `{"input":…,"output":…,"input_cached_tokens":…,"input_cache_creation":…}` from the four
    token attributes, when all four exist. Copying them to `gen_ai.usage.*` was tried first.
    Langfuse read `gen_ai.usage.input_tokens` as cache-inclusive and subtracted the cache,
    so every cached request showed input 0. Langfuse stores `usage_details` keys verbatim.
  * `langfuse.trace.tags` = `["task:<task_id>", "attempt:<attempt_id>"]` when the resource has
    `task_id`. Langfuse filters on tags, not on resource attributes, so the tags go on every
    span.

  Straight export to Langfuse would leave the usage unmapped and the task unfilterable.
* **Traces only for launched sessions.** User-scope trace variables would send the spans of
  every session on the machine, other checkouts and consumer sandboxes included, to this
  Langfuse project. Only the Langfuse keys, which Alloy reads, live at User scope.
* **Metrics and logs stay direct.** Claude Code puts the resource attributes on every
  datapoint itself, so the collector adds nothing. Rerouting them would put the Grafana
  series behind a new failure point.
* **The Codex chain leaves Alloy.** Its metric pipeline was dead
  ([ADR 0033](0033-claude-code-is-the-only-carrier.md)). Its required `GRAFANA_CLOUD_*`
  variables no longer existed, so `run-alloy.ps1` could not restart Alloy. The script now
  requires the Langfuse keys.
* **No content.** `OTEL_LOG_USER_PROMPTS` and `OTEL_LOG_TOOL_DETAILS` stay unset, so prompts
  arrive as `<REDACTED>`.
* **The plugin is uninstalled.** It was at user scope, so its hook traces came from every
  project. Its `pluginConfigs` entry and its marketplace were removed with it.

Fields sent to Langfuse, from the probe and the gate (2.1.295–2.1.296):

* Resource: `service.name`, `service.version`, `service.instance.id`, `os.type`,
  `os.version`, `host.arch`, `vcs.repository.name`, `vcs.repository.url.full`, `task_id`,
  `attempt_id`.
* Every span: `session.id`, `span.type`, `terminal.type`, `user.id`, `user.email`,
  `user.account_id`, `user.account_uuid`, `organization.id`, the two `vcs.repository.*`
  pairs.
* `claude_code.llm_request`: the four token counts, `model`, `gen_ai.request.model`,
  `gen_ai.system`, `gen_ai.response.id`, `gen_ai.response.finish_reasons`, `stop_reason`,
  `request_id`, `client_request_id`, `attempt` (API retry, not `attempt_id`), `success`,
  `duration_ms`, `ttft_ms`, `first_content_ms`, `effort`, `speed`, `query_source_safe`,
  `llm_request.context`, `agent_id` in a subagent.
* `claude_code.interaction`: `user_prompt` (`<REDACTED>`), `user_prompt_length`,
  `interaction.sequence`, `interaction.duration_ms`, `parent.source`, `queued_sends`.
* `claude_code.tool`, `.tool.execution`, `.tool.blocked_on_user`: `tool_name`,
  `tool_name_safe`, `tool_use_id`, `gen_ai.tool.call.id`, `success`, `duration_ms`,
  `decision`, `source`.

The account fields are accepted: the Langfuse project is the owner's, and the plugin sent
more.

### Gate

One throwaway session ran through the launcher: three `claude -p` turns joined by
`--resume`, one tool call and one Explore subagent. The Grafana total per type is

```
sum by (type) (max_over_time(claude_code_token_usage_tokens_total{session_id="<id>"}[<window>]))
```

with a window covering the session. The User scope sets cumulative temporality, so each
series counts from zero for its process. `increase()` is not used: it extrapolates and drops
a new series' first sample. The Langfuse side sums the usage details of the session's
generations (v2 observations, metadata `attributes.session.id`).

| type | Langfuse | Grafana |
|---|---|---|
| input | 1 200 | 1 200 |
| output | 945 | 945 |
| cacheRead | 311 292 | 311 292 |
| cacheCreation | 59 607 | 59 607 |

All nine `claude_code.llm_request` spans arrived as generations with the four usage keys and
the tags `task:issue-<N>` and `attempt:1`. Every Grafana series carried `task_id` and
`attempt_id`. A session started without the launcher sent no trace. Its Grafana series
carried `vcs_repository_name` without `task_id`.

### Consequences

* Good, because one stream feeds both backends, and they agree type by type on one session.
* Good, because a Langfuse trace and a Grafana series of one task are found by the same
  identity.
* Bad, because the owner supplies the identity. A session started without the launcher has
  no traces, and its Grafana series has no `task_id`. A wrong issue or attempt number is
  attributed to the wrong task, and only the visible tags show it.
* Bad, because the traces are a beta. A release can rename spans or attributes, and the
  Langfuse usage then drops while the Grafana totals stay.
* Bad, because Claude Code processes started while the previous route sent their metrics to
  the collector kept that environment. Their metrics stopped reaching Grafana when the
  traces-only Alloy replaced the old one, until they were restarted.
* Neutral: the per-task readings consume the labels and tags. They reject a measured window
  that contains a series of the measured repository without `task_id`, or one whose
  per-type Langfuse usage differs from the Grafana total.

### Reconsider condition

* A Claude Code release changes the trace schema. The per-type comparison in the per-task
  readings catches it.
* Claude Code accepts a per-session resource attribute beside a settings value, which would
  make the launcher unnecessary.
* Langfuse maps Anthropic's cache-exclusive input from `gen_ai.usage.*`, which would remove
  the `Concat` statement.

### Confirmation

`tests/agent_process/test_task_session.py` covers the launcher. The gate readings above were
taken live, because both ingest paths are third-party.
