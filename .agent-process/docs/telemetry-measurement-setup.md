# Agent telemetry measurement setup

**Question this document answers:** how agent token usage is exported, where it
lands, which labels identify the project and the task it was spent on, and how one
task's time to merge, review rounds, cost, failed and denied calls and compactions are
read.

This is the owner-side setup that the token-efficiency measurement depends on.
Every claim below was observed, not read out of vendor documentation, and the
claims that contradict the documentation are marked.

## What exports what

| Route | Switch | Lands in | Token categories |
| --- | --- | --- | --- |
| Metrics, logs | `CLAUDE_CODE_ENABLE_TELEMETRY=1` plus the `OTEL_EXPORTER_OTLP_*` transport variables | Grafana Cloud: `claude_code_token_usage_tokens_total`, Loki | `type` ∈ `input` / `output` / `cacheRead` / `cacheCreation` |
| Traces (beta) | the launcher's settings layer (below) | Langfuse, through the local Alloy collector | usage details `input` / `output` / `input_cached_tokens` / `input_cache_creation` |

Metrics and logs push OTLP straight to Grafana Cloud: metrics to the Prometheus
datasource, logs to the Loki datasource. The transport variables (endpoint, protocol,
headers), the service-account token and the Langfuse keys live in the owner's Windows
User-scope environment and are deliberately absent from this repository — nothing here
reads them, and nothing here should print them.

Dashboards are referred to by UID rather than by URL, for the same reason:
`agwhkq` and `axwvz9`.

The decision and the gate readings are in
[ADR 0037](adr/0037-one-emitter-feeds-both-telemetry-backends.md).

## Which label carries the project

`.claude/settings.json` sets `OTEL_RESOURCE_ATTRIBUTES` to a comma-joined
`key=value` list:

```
vcs.repository.name=<owner>/<repository>,vcs.repository.url.full=https://github.com/<owner>/<repository>
```

Each adoption carries its own value, never this repository's. An adopter sets
the pairs by hand: telemetry left the v2 migration
([ADR 0029](adr/0029-telemetry-leaves-the-v2-migration.md)).
The URL pair is omitted when the repository has no canonical GitHub URL;
a guessed one is worse than an absent one.

`vcs.repository.name` and `vcs.repository.url.full` are documented OpenTelemetry
registry attributes, not invented keys. The identifying attributes
`service.namespace` and `service.instance.id` were rejected as the project carrier: the
OTLP-to-Prometheus translation folds them into `job` and `instance`, which would
orphan the series already accumulated under `job="claude-code"`. The launcher sets
`service.instance.id` per process for another reason (below).

**Observed, not assumed:** the dotted keys survive the translation as
`vcs_repository_name` and `vcs_repository_url_full`, and they arrive **as labels
on the token series**, not only on `target_info`. All four `type` values carry
them. A Prometheus query filtered on this project's value returns the token
series; the same query with another project's value returns nothing.

In Loki the pairs ride as **per-entry structured metadata**, not as indexed
stream labels — `service_name` is the only indexed label — so a Loki query must
select on `service_name` first and filter on the project afterwards.

The carrier is a **list from the first commit** on purpose. `OTEL_RESOURCE_ATTRIBUTES`
is one string with no merge semantics, and the per-task attributes are appended to
the same variable.

A tree with a `.claude/settings.json` that lacks the `env` key gets no attribution
from the process: it gets the key by hand or it stays unlabelled. That is the safe
direction — an unlabelled tree reads on the dashboard as "not this project" rather
than being silently folded in.

## Which labels carry the task

A session launched for a task gets its identity from the owner launcher, the same in
PowerShell and Git Bash:

```
python .agent-process/scripts/task_session.py --issue <N> [--attempt <K>] -- claude [args...]
```

It inserts one `--settings` JSON after `claude`. Its `env` holds the project's
`OTEL_RESOURCE_ATTRIBUTES` plus `task_id=issue-<N>,attempt_id=<K>,service.instance.id=<uuid4>`
and the four trace variables:

```
CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://127.0.0.1:4318/v1/traces
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
```

`--attempt` defaults to 1. The process environment cannot carry the identity: the
project's settings value replaces it (precedence, below).

**Observed:** the token series carry `task_id`, `attempt_id` and `instance`; `job` stays
`claude-code`. A resumed session is a new process whose cumulative counters restart from
zero, and `instance` keeps each process on its own series. Without it the reset hides the
earlier process's tokens from the per-session query below.

A session started without the launcher sends no trace, and its series and events carry
`vcs_repository_name` without `task_id`. Rule 1 of [Per-task metrics](#per-task-metrics)
decides when such a session makes a window not attributable.

## Traces through Alloy to Langfuse

Local Grafana Alloy listens on `127.0.0.1:4318` with a traces-only pipeline. Its
configuration lives on the owner's machine, outside this repository: it is host state,
not project state, and a consumer of this template must not inherit it. Changing it is
an owner decision each time. The pipeline, without secrets:

```alloy
otelcol.receiver.otlp "claude_code" {
  http { endpoint = "127.0.0.1:4318" }
  output { traces = [otelcol.processor.transform.langfuse.input] }
}

otelcol.processor.transform "langfuse" {
  error_mode = "ignore"
  trace_statements {
    context    = "span"
    statements = [
      `set(attributes["langfuse.observation.usage_details"], Concat(["{\"input\":", attributes["input_tokens"], ",\"output\":", attributes["output_tokens"], ",\"input_cached_tokens\":", attributes["cache_read_tokens"], ",\"input_cache_creation\":", attributes["cache_creation_tokens"], "}"], "")) where attributes["input_tokens"] != nil and attributes["output_tokens"] != nil and attributes["cache_read_tokens"] != nil and attributes["cache_creation_tokens"] != nil`,
      `set(attributes["langfuse.trace.tags"], [Concat(["task:", resource.attributes["task_id"]], ""), Concat(["attempt:", resource.attributes["attempt_id"]], "")]) where resource.attributes["task_id"] != nil`,
    ]
  }
  output { traces = [otelcol.processor.batch.langfuse.input] }
}

otelcol.processor.batch "langfuse" {
  output { traces = [otelcol.exporter.otlphttp.langfuse.input] }
}

otelcol.auth.basic "langfuse" {
  username = sys.env("LANGFUSE_PUBLIC_KEY")
  password = sys.env("LANGFUSE_SECRET_KEY")
}

otelcol.exporter.otlphttp "langfuse" {
  client {
    endpoint = "https://cloud.langfuse.com/api/public/otel"
    auth     = otelcol.auth.basic.langfuse.handler
    headers  = { "x-langfuse-ingestion-version" = "4" }
  }
}
```

`run-alloy.ps1` starts Alloy only when both Langfuse key variables are set.

**Observed, against the documentation's suggestion:** Langfuse reads
`gen_ai.usage.input_tokens` as including the cached tokens and subtracts them, so an
Anthropic request with cache reads shows input 0. The flat `usage_details` JSON is
stored verbatim. Langfuse filters on trace tags, not on resource attributes, so the
transform puts the tags on every span.

Prompts arrive as `<REDACTED>`: `OTEL_LOG_USER_PROMPTS` and `OTEL_LOG_TOOL_DETAILS` stay
unset.

## Per-session totals

The Grafana total per type for one session, or for one task attempt with
`task_id="issue-<N>",attempt_id="<K>"` in place of the `session_id` matcher:

```promql
sum by (type) (max_over_time(claude_code_token_usage_tokens_total{session_id="<id>"}[<window>]))
```

with a window covering the session or the attempt. The User scope sets cumulative
temporality, so each series counts from zero for its process. `increase()` is not used: it
extrapolates and drops a new series' first sample. For the same session, the sum of
Langfuse usage details over its generations equals this total type by type; for a task
attempt, the generations are those tagged `task:issue-<N>` and `attempt:<K>`. A window
where they differ points at a trace-schema change of the beta. The sum holds only for
series that carry `instance`; a process without it can lose tokens to the reset
described under [Which labels carry the task](#which-labels-carry-the-task).

## Per-task readings

One task's delivery reading is four reads, owner-side, by hand. `<change>` is the change
name, which is also the branch `start_change` creates.

```
# Start: the task's first token sample, a PromQL query in Grafana
min(min_over_time(timestamp(claude_code_token_usage_tokens_total{task_id="issue-<N>",attempt_id="<K>"})[30d:1m]))

# Merge time and size (additions plus deletions, plan artifacts included)
gh pr list --head <change> --state merged --json number,mergedAt,additions,deletions

# Code rounds: the distinct heads the review job read; one round is no rework
gh pr view <number> --json comments --jq '[.comments[] | select(.author.login=="github-actions") | .body | split("\n")[0] | capture("^Reviewed head SHA: (?<s>[0-9a-f]+)$").s] | unique | length'

# Plan rounds: the archived review's round; a review written before the field has none
grep '"round"' openspec/changes/archive/*-<change>/architect-review.json
```

Exact matchers keep sessions without the launcher out of the start, so such a session
leaves it late or empty. Grafana keeps about 14 days of samples: read the start at merge.

| Task | Start | Merged | Hours | Lines | Plan rounds | Code rounds | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `task_id=issue-101`, `attempt_id=1` (baseline) | 2026-10-10T15:02:36Z | 2026-10-10T16:19:44Z | 1.29 | 998 | gap | 3 | First launched for the task-identity gate, after its planning ran without the launcher: the start is late. |

## Per-task metrics

A task's cost, failed and denied tool calls, and context compactions come from two Loki
queries, run in Explore over a time range that covers the task's sessions. Every event
attribute is per-entry structured metadata, so label filters and `unwrap` read it with no
parser stage. `<owner>/<repo>` is the measured repository.

```logql
# Cost in USD
sum by (task_id, attempt_id) (sum_over_time(
  {service_name="claude-code"} | vcs_repository_name="<owner>/<repo>"
  | task_id=~"issue-[0-9]+" | event_name="api_request"
  | unwrap cost_usd [$__range]))

# Counts, also the input of rule 1
sum by (task_id, attempt_id, event_name, success, decision) (count_over_time(
  {service_name="claude-code"} | vcs_repository_name="<owner>/<repo>"
  | event_name=~"api_request|tool_result|tool_decision|compaction" [$__range]))
```

`$__range` is the whole selected range, so run them as instant queries; an hourly range
query takes `[1h]` instead, or each step counts the whole range again.

- **Failed** is the `tool_result` row with `success="false"`. The event also carries an
  `error_type`.
- **Denied** is the `tool_decision` row with `decision="reject"`, from any `source`
  (`hook`, `config`, `user`). A rejected call emits no `tool_result`, so failed and
  denied are disjoint and add up to the failed-plus-denied count.
- **Compactions** is the sum of the `compaction` rows, which split by the event's own
  `success`. The event also carries `trigger`, `pre_tokens` and `post_tokens`.
- **Cost** is read from the events, not from `claude_code_cost_usage_USD_total`: the
  counter loses a reset process's cost, the events do not. Subagent requests are
  `api_request` events of the same session and are included.

**Observed:** `cost_usd` prices the cache write at the 1-hour rate (2× input) that the
sessions use, not at the 5-minute rate. Checked on one request with Claude Code 2.1.296;
repeat the check on a newer version before relying on it.

An absent row is a zero only when its field is shown to exist. The `success="true"` and
`decision="accept"` rows show it for failed and denied, and a row with an empty field
means a rename. A compaction has no such companion: a missing `compaction` row is 0 only
if the counts query over the whole Loki retention returns some `compaction` row of the
repository; otherwise the reading is missing. A task with no cost row exported nothing
and is recorded as missing, not as zero.

A window is rejected when either rule holds:

1. The counts query returns a row whose `task_id` is not `issue-<N>`: a session of the
   repository ran without the launcher. An absent `task_id` reads as empty, and the
   retired collector route's `unassigned` value fails the pattern too. The launcher sets
   the identity once for events, metrics and traces, so such a session shows in all
   three. The rejection records which value caused it.
2. The [Per-session totals](#per-session-totals) comparison with the task selector
   differs for some type.

The task-identity gate's attempt reads cost 1.1960044 USD, 0 failed, 0 denied and
0 compactions, with 22 `api_request` events. Rule 1 rejects its window: its planning
session ran without the launcher in the same hour, with 4 `api_request` events and no tool
call — which is why the counts query matches `api_request`.

Loki keeps about 14 days of events: read a task within that time after its last
session.

## Two failure conditions that are usually silent

The vendor documentation names two conditions under which a settings `env` block
does not take effect. Both were exercised on Claude Code 2.1.265 / 2.1.268, and
**neither reproduced**:

- **Relaunch.** A session that was already running when the settings file was
  written picked up the new value, and picked up a second value after a second
  write — two distinct label values matching the two writes, with no relaunch.
- **Folder trust.** A settings `env` block in a directory Claude Code had never
  run in before was applied by a headless run. The interactive first-run trust
  prompt was not exercised, so that half remains untested.

Record both as *not reproduced here*, not as *does not apply*. A reader on a
different version must check rather than rely on either direction. The direction
that matters for a mistake is cheap to check: query the token series for
`vcs_repository_name` and see whether the current project's value is present.

**Precedence is observed, and it is the sharp edge for an adopter.** With a
settings `env` value and an inherited process-environment value of the same
variable set at the same time, the **settings value wins outright**: the
process-environment value appears nowhere in the telemetry. A settings-level
`OTEL_RESOURCE_ATTRIBUTES` therefore *replaces* an adopter's own resource-attribute
set rather than adding to it. An adopter who already sets that variable loses
their attributes silently once the process writes the settings value, and must
fold their own pairs into that value by hand.
