---
status: "accepted"
date: 2026-10-09
decision-makers: ekolvah
---

# Per-task totals stay on Grafana; the Langfuse plugin route fails

## Context and Problem Statement

[ADR 0029](0029-telemetry-leaves-the-v2-migration.md) leaves the per-task telemetry backend
to a Langfuse evaluation. Langfuse models a task natively (trace, generations, tool calls,
usage per observation) and ships an official Claude Code plugin; the Grafana stack
reconstructs a task from labels. A bounded spike ran the plugin on real tasks of this
repository against a criterion fixed before any number was read:

> Langfuse becomes the per-task analysis backend if M1 (input-equivalents per task), M3 (API
> round trips per task), M4 (mean prompt size per request), M5 (tool failure rate,
> compaction count) and M6 (wall time per task) are readable per task without code beyond
> the plugin and its configuration, and the numbers cross-check against `ccusage`. If any
> fails, per-task analysis continues on Grafana and this record names the failed criterion.

The Codex half of the original criterion is dropped: Claude Code is the only carrier
([ADR 0033](0033-claude-code-is-the-only-carrier.md)).

What was run:

* Plugin `langfuse/Claude-Observability-Plugin` `v1.2.1`, commit
  `b5b7cc364996467e856dc17575b5674f4799ad87`, installed at local scope from a clone of that
  commit. Its hook script declares `langfuse>=4.7,<5`; `UV_EXCLUDE_NEWER` froze it at
  `langfuse==4.17.0`, wheel sha256
  `02560e12d715dd24f239c240886ee197b9e62f4a808f06de77193356c56bf57a`.
* Egress: Langfuse Cloud, EU region, images off. The owner chose it against the vetted
  payload, before the first trace: prompts, assistant output including thinking, full tool
  inputs and results, subagent prompts, the working directory path. Reason: the plugin
  default, no infrastructure for a bounded window; images add a second host and nothing to
  the metrics.
* Keys: the plugin declares the secret key `sensitive`, but on Windows it is stored in the
  plain-text `~/.claude/.credentials.json`, beside Claude Code's own OAuth token, not in the
  OS credential store. The owner accepted that.
* Task identity: each session was launched with `CC_LANGFUSE_TRACE_TAGS=task:<change>,attempt:<n>`.
  The tags reach every trace, and a tag filter returns exactly the sessions launched under
  it.
* Four changes, a propose and an apply session each; one had its propose session lost
  (below). Readings use the public `v2/observations` and `v2/metrics` endpoints; the legacy
  traces and metrics endpoints answer 410 for organizations created after 2026-09-16.

## Readings

Per change, implementer side (main agent plus subagents), after the duplicate repair below:

| change | sessions | M3 generations | M4 mean prompt | M5 tool failures | M6 turn time | USD (Langfuse price table) |
|---|---|---|---|---|---|---|
| guard-unwraps-clustered-shell-flags | apply only | 219 | 89 263 | 17/313 = 5.4 % | 7 h 50 min¹ | 11.18 |
| bound-review-closing-comment | 2 | 84 | 76 256 | 1/94 = 1.1 % | 36 min | 3.99 |
| plugin-env-locks-rebuild | 2 | 118 | 80 924 | 4/140 = 2.9 % | 53 min | 6.93 |
| edit-lint-surfaces-git-failure | 2 | 126 | 82 838 | 6/143 = 4.2 % | 52 min | 5.39 |

¹ Sum of turn spans; a turn span includes idle time inside the turn.

M3 is the count of `GENERATION` observations, M4 the average of `inputTokens` per
generation, M5 the share of tool observations at level `ERROR`, M6 the summed latency of
the root turn spans. Each is one Metrics API query filtered by the task tag.

Cross-check: for every delivered session, input, output, cache-creation and cache-read
totals and the generation count equal `ccusage@20.0.26 session --id <id> --offline`
exactly, after the repair.

## Considered Options

* Grafana, fed by Claude Code's own OpenTelemetry metrics and events.
* Langfuse, fed by the official Claude Code plugin's transcript hook.

## Decision Outcome

Chosen: **per-task totals stay on Grafana; the plugin route does not become the per-task
backend.** The criterion fails on three counts:

* **M1 needs code.** The Metrics API exposes `inputTokens` as one sum of fresh input, cache
  creation and cache read. It has no cache measures, so the input-equivalent weights (1.0,
  1.25, 0.1) cannot be applied. `totalCost` in USD from Langfuse's price table is
  readable, but that is a different metric.
* **M5 compaction count is not sent.** The plugin emits no compaction observation. The
  transcripts of the measured sessions hold three compactions; Langfuse shows none.
* **The numbers do not cross-check without manual repair.** The plugin answers every
  failure with exit 0 and keeps its state keyed on
  `sha256(session_id::resolved transcript_path)`. That produced two silent faults:
  * Claude Code allows SessionEnd hooks 1.5 s by default. The plugin holds the open turn
    for SessionEnd, so one session whose only turn was held there was killed with 0
    observations sent. Raising `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` fixed delivery.
  * After `EnterWorktree`, Stop payloads carry the transcript path under the worktree's
    project directory, and SessionEnd carries the launch directory's. The two keys do not
    share progress, so SessionEnd re-sent turns the Stops had shipped. Every apply session
    that entered a worktree doubled its token totals (three of three).

  Trace ids are deterministic, but observation ids are not, so a re-run doubles rather than
  overwrites. Each doubled session was repaired by deleting its traces and replaying
  SessionEnd once into an empty session. The lost session cannot be recovered: the plugin
  marks a turn as sent before its flush.

M3, M4, the tool failure rate of M5 and M6 are readable without code. So are the tags.

### Consequences

* Good, because the readings above are a first per-task baseline for M3–M6, implementer
  side.
* Good, because the faults are named: a second, hook-based emitter beside Claude Code's own
  OpenTelemetry export cannot agree with it on totals.
* Bad, because the owner runs two backends fed by two emitters until one emitter feeds
  both. Langfuse stays in use for per-turn inspection (which tool call, which turn); the
  delivery faults above apply to any total read from it.
* Neutral: the next step is one emitter. Claude Code's own OpenTelemetry export, with its
  traces beta, goes through the owner's collector to both Grafana and Langfuse's OTLP
  endpoint, with the task identity as a resource attribute. The per-task telemetry change
  plans it.

### Reconsider condition

Repeat this comparison when any holds:

* The process moves to its own orchestration on the Agent SDK. Langfuse SDK
  instrumentation and Datasets/Experiments then apply directly, without a transcript hook.
* A plugin release keys its state on the session alone, or otherwise survives
  `EnterWorktree`, and emits compactions. In addition, Langfuse's Metrics API exposes cache
  usage, or a custom model price in input-equivalent units is shown to turn `totalCost`
  into M1.
* Claude Code's traces reach Langfuse through the collector with token usage on each
  request span, so both backends read one stream.

### Confirmation

This record exists, and the per-task telemetry change is planned against one
OpenTelemetry stream feeding both backends.
