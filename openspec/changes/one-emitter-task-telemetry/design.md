## Context

See proposal.md, Why, for the observations this design rests on.

Owner host today: Claude Code exports metrics and logs straight to Grafana Cloud (User-scope
`OTEL_EXPORTER_OTLP_*`). Local Alloy 1.18.1 listens on `127.0.0.1:4318` with a metrics-only
pipeline left from the Codex route (receiver `codex`, filter, transform, delta-to-cumulative,
batch, Grafana exporter). It is started by `~/.config/alloy/run-alloy.ps1` and reads its
secrets with `sys.env`. The Langfuse plugin is installed at local scope in the main checkout
([ADR 0036](../../../../.agent-process/docs/adr/0036-per-task-token-analysis-backend.md)).
The project's `.claude/settings.json` sets `OTEL_RESOURCE_ATTRIBUTES` to the two
`vcs.repository.*` pairs ([ADR 0026](../../../../.agent-process/docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md)).

## Goals / Non-Goals

**Goals:**

- A session that the owner launches for an issue carries `task_id` and `attempt_id` on its
  Grafana token series and as tags on its Langfuse traces. Both come from one emitter.
- For one session, Langfuse usage equals the Grafana token totals, type by type.

**Non-Goals:**

- Traces in Grafana Tempo: no reader exists for them.
- Removing the dead Codex metric chain from `config.alloy`: unrelated host cleanup.
- M1–M6 readings, dashboards, outcome resolution, and a compaction signal: #99 consumes
  the labels and tags.
- Prompt, response or tool content in Langfuse.

## Decisions

### D1 Identity: a `--settings` JSON layer composed by an owner launcher

`task_session.py --issue N [--attempt K] -- <command…>` reads `env.OTEL_RESOURCE_ATTRIBUTES`
from `.claude/settings.json` of the current Git top level and appends
`task_id=issue-N,attempt_id=K`. It runs the command with `--settings <json>` inserted after
its first element, and exits with the command's exit code. The JSON's `env` holds that value
and the four trace variables of D2. `claude --help` (2.1.295) documents
`--settings <file-or-json>`, so no temporary file is written. A settings `env` layer turned
on the telemetry exporters in a shell that had none (issue 101 comment of 2026-09-12).

`attempt_id` is a resource attribute. The `attempt` attribute on `claude_code.llm_request`,
seen in the probe, is a different field (the API request retry) and does not collide.

- The process environment cannot carry the value: the project's settings value replaced it
  (proposal, Why).
- Editing `.claude/settings.local.json` was rejected because parallel sessions share one
  checkout and the file outlives the session.
- A hand-typed `claude --settings '<json>'` is the standard. It does not fit because each
  launch has to repeat the project pairs exactly, or the repository label is lost. The JSON
  also has to be quoted for a native executable differently in PowerShell and in Git Bash.
- The launcher exits 2, naming the cause, when `N` or `K` is not a positive integer, when
  the project sets no `OTEL_RESOURCE_ATTRIBUTES`, or when that value already names
  `task_id` or `attempt_id` (§VI).
- The command runs through an injected runner (§II), so the tests observe the argument list
  without starting Claude.

`--attempt` defaults to 1. The owner sets it explicitly for a later attempt, as in the ADR
0036 spike. The v1 attempt ledger was dropped: it stored a decision that the owner makes
anyway.

The owner now supplies the identity. Its failure modes and what catches each:

- **A launch without the launcher.** The session sends no traces, and its Grafana series
  carry this repository's `vcs_repository_name` without a `task_id` label. #99 rejects a
  measured window that contains such a series (task 8.4 hands it this rule).
- **A wrong issue or attempt number.** The work is attributed to the wrong task, and
  nothing catches it automatically. The tags are visible on every trace, so the owner can
  see the error.

### D2 Route: traces through Alloy, metrics and logs direct

The launcher's settings layer (D1) sends traces to the local receiver:
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, `OTEL_TRACES_EXPORTER=otlp`,
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:4318/v1/traces`,
`OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf`. Only launched sessions trace. Host-wide
User-scope variables were rejected: every session on the machine, in other checkouts and
consumer sandboxes too, would send spans with account fields to this Langfuse project. Only
the Langfuse keys, which Alloy reads, live at User scope.

Metrics and logs stay direct. Claude Code puts the resource attributes on every datapoint
itself (ADR 0026, observed), so Alloy adds nothing to them. Rerouting them would put the
Grafana series behind a new failure point.

Exporting straight to Langfuse was rejected: Langfuse reads neither the usage attributes
nor resource attributes as filterable fields (D3).

### D3 Alloy: one traces pipeline with a standard transform

The `codex` receiver gains a `traces` output. The new chain is
`otelcol.processor.transform "langfuse"` → `otelcol.processor.batch "langfuse"` →
`otelcol.exporter.otlphttp "langfuse"`. The exporter sends to
`https://cloud.langfuse.com/api/public/otel` with `otelcol.auth.basic`, whose username and
password are the public and secret keys from `sys.env`, and the header
`x-langfuse-ingestion-version: 4`. The transform runs these span-context statements:

- When the source attribute exists, copy `input_tokens`, `output_tokens`,
  `cache_read_tokens` and `cache_creation_tokens` to `gen_ai.usage.input_tokens`,
  `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read_input_tokens` and
  `gen_ai.usage.cache_creation_input_tokens`.
- `langfuse.trace.tags` = `["task:<task_id>", "attempt:<attempt_id>"]` from the resource
  when `task_id` is present. The tags go on every span, because Langfuse filters per
  observation.

The `gen_ai.usage.*` names are the OpenTelemetry GenAI convention, which Langfuse documents
as a usage source. If the gate (D5) shows the cache keys missing from Langfuse usage, the
fallback is one `langfuse.observation.usage_details` JSON built with `Concat`. The tag
format is the one of the ADR 0036 spike. `otelcol.processor.transform` is the standard,
already in this config.

### D4 No content in Langfuse

`OTEL_LOG_USER_PROMPTS` and `OTEL_LOG_TOOL_DETAILS` stay unset. Prompts arrive as
`<REDACTED>`. Per-turn inspection keeps the turn, the model, the tool name, success, the
duration and the tokens. Once the plugin is gone, Langfuse no longer shows transcript text;
this is a deliberate reduction of egress. The owner can turn either gate on later without a
change to this design.

### D5 Live gate with an early exit

Grafana metrics and Langfuse traces are third-party ingest paths, so the gate is live, not
under CI, and is recorded in `evidence/issue-101/`. One throwaway session is launched through
`task_session.py`, with at least three turns, one tool call and one subagent. The gate
passes when all three hold:

- (a) Langfuse shows each `claude_code.llm_request` as a generation whose usage carries
  input, output, cache read and cache creation, with the trace tags `task:` and `attempt:`.
- (b) Grafana `claude_code_token_usage_tokens_total` for that `session_id` carries
  `task_id` and `attempt_id`.
- (c) For that session, the sum of Langfuse usage equals the Grafana total for each of
  the four types.

The Grafana total is
`sum by (type) (max_over_time(claude_code_token_usage_tokens_total{session_id="<id>"}[<window>]))`,
with a window covering the session. The User scope sets cumulative temporality (observed),
so each series counts from zero for its session. PromQL `increase()` is not used: it
extrapolates and drops a new series' first sample. No external reference calibrates the
query: ccusage counts transcript messages, while both sides of (c) count every API request,
side requests such as `generate_session_title` included (probe).

If (a) fails with both mappings of D3, or the traces do not arrive, the host is rolled back
(Migration Plan). ADR 0037 then records the failure, the plugin stays, and the launcher
ships for the Grafana half alone. If only (c) fails, the change stops before the PR and the
divergence is reported to the owner, with the query (window, series selection) as the first
suspect.

## Risks / Trade-offs

- [The traces beta changes span names or attributes in a Claude Code release, which
  updates itself] → Langfuse usage drops while the Grafana totals stay. #99 catches it: it
  rejects a measured window whose per-type Langfuse usage differs from the Grafana total
  (task 8.4 hands it this rule).
- [The generic `OTEL_EXPORTER_OTLP_HEADERS`, which holds the Grafana token, is also sent on
  the traces request] → it reaches only `127.0.0.1`. The Alloy `otelcol.receiver.otlp`
  reference describes `include_metadata` as "Propagate incoming connection metadata to
  downstream consumers", default `false`. Task 3.2 checks that the candidate does not set
  it.
- [Account fields such as `user.email` and `organization.id` ride on every span to
  Langfuse] → accepted. This is the owner's own project, and the plugin already sent more.
  ADR 0037 records the field list from the probe.
- [Alloy restart] → only the dead Codex metrics and the new traces depend on Alloy. The
  Grafana metrics and logs route does not pass through it.

## Migration Plan

1. Back up `config.alloy` as `config.alloy.one-emitter.pre` and record the User-scope
   variable names that will change.
2. Validate the candidate with the installed `alloy.exe validate
   --stability.level=experimental` before replacing the config. Restart through
   `run-alloy.ps1` and verify that `127.0.0.1:4318` listens.
3. Set the Langfuse key variables at User scope and restart Alloy so that it reads them.
4. Gate D5. When it passes, uninstall the Langfuse plugin and remove its settings entries.
5. Rollback, on an early exit or on owner request: restore the backup, restart Alloy, and
   delete the key variables. On an early exit the D2 variables also leave the launcher
   before the PR. The plugin is untouched until step 4.
