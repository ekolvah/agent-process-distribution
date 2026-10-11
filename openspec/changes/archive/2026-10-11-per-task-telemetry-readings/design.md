## Context

See proposal.md (Why) for the observations, and the setup document's "Which labels carry
the task" and "Per-session totals" sections for the identity and the existing
Langfuse-vs-Grafana check. New here: in Loki, `service_name` is the only indexed label.
Every event attribute is structured metadata, including `event_name`, `task_id`,
`attempt_id`, `vcs_repository_name`, `cost_usd`, `success`, `decision` and `source`
(observed on 2026-10-10). Label filters and `unwrap` therefore read them with no parser
stage. The oldest Loki event of the service is from 2026-09-27, about 14 days back.

## Goals / Non-Goals

**Goals:**

- Two Loki queries, keyed by `task_id` and `attempt_id`, give all three metrics for any
  launched task.
- The two window-rejection rules can be applied by hand when a task is read. The setup
  document states each rule once.

**Non-Goals:**

- No script, scheduled job, alert, Loki recording rule, or dashboard panel (D5).
- No change to the launcher or to session identity.

## Decisions

### D1. Two Loki queries give the three metrics

Cost:

```logql
sum by (task_id, attempt_id) (sum_over_time(
  {service_name="claude-code"} | vcs_repository_name="<owner>/<repo>"
  | task_id=~"issue-[0-9]+" | event_name="api_request"
  | unwrap cost_usd [$__range]))
```

Counts:

```logql
sum by (task_id, attempt_id, event_name, success, decision) (count_over_time(
  {service_name="claude-code"} | vcs_repository_name="<owner>/<repo>"
  | event_name=~"api_request|tool_result|tool_decision|compaction" [$__range]))
```

The counts query has no task filter, so its rows also serve rule 1 (D2). It includes
`api_request` because a plain session can make no tool call at all. The gate's plain
session did exactly that, with 4 `api_request` events and no tool event, observed during
implementation.

- **Failed** is the `tool_result` row with `success="false"`.
- **Denied** is the `tool_decision` row with `decision="reject"`, from any `source`.
- **Compactions** is the sum of the `compaction` rows. The event has its own `success`
  field, so these rows split by it.

The `success="true"` and `decision="accept"` rows show that a field is present. A
missing counted row then means 0, while a row with an empty field means a rename. The
`compaction` event has no such companion row. A missing compaction row therefore means 0
only if the counts query over the repository's whole Loki retention returns some
`compaction` row. Otherwise the reading is recorded as missing. Failed
and denied are disjoint (proposal, Denials), and together they are the issue's "failed
plus denied". Subagent requests are `api_request` events of the same session, so they
are included.

Alternatives:

- `claude_code_cost_usage_USD_total`. It undercounts across a counter reset (proposal,
  Source) and has no counterpart for decisions or compactions. One source avoids a
  reconciliation.
- Langfuse generation cost. Langfuse prices requests from its own model table and
  receives only launched sessions.
- One query per metric. That means four scans of the same stream, plus a manual presence
  check for each count.

### D2. Rule 1 reads events

A window is rejected when the D1 counts query returns a row whose `task_id` is not
`issue-<N>`. A missing `task_id` reads as empty, and the retired collector route's
`unassigned` value fails the pattern too. The setup document's current sentence (an
unlaunched *series* makes the window not attributable) is rewritten to point at this
rule, so the document states the rule once. The launcher sets the identity once for
events, metrics and traces, so a session without it shows up in all three. Reading the
same source as D1 keeps one window meaning one thing.

### D3. Rule 2 reuses the per-session totals check with a task selector

The "Per-session totals" query and its Langfuse comparison change to accept either
`session_id` or `task_id` with `attempt_id`. They are not copied. When a task is read, the
check runs through the Langfuse API or MCP for each task. Any difference rejects the
task's window. The counter is safe here because every launched process has its own
`instance` series. The undercount in the proposal predates `service.instance.id`.

Alternative: an Infinity-datasource panel calling the Langfuse API. Rejected because it
would put Langfuse keys in Grafana Cloud for a check that runs five times.

### D4. No baseline

The owner tracks the metrics across later tasks and skill experiments instead of recording
a baseline (decision 2026-10-11). Loki keeps about 14 days of events, so a task is read
within that time. A task with no cost row exported nothing. It is recorded as missing and
not as zero, which catches a session that rule 1 cannot see. The cost check of the
proposal is repeated only when the Claude Code version is newer than 2.1.296.

Alternative: Loki recording rules that copy the readings into Prometheus for longer
retention. Rejected because it adds new ruler state on the host before any reading has
needed more than 14 days.

### D5. No ADR, no new check, no dashboard panel

The readings use the identity that ADR 0037 decided, and no observed failure calls for a
script. A per-task panel on `axwvz9` was rejected: Explore runs the document's queries
for five readings without new host state. Reconsider the panel once #99 reads the
metrics repeatedly.

## Risks / Trade-offs

- [Rule 1 also rejects a window that holds an unrelated plain session of the repository,
  such as a parallel VS Code session once its export returns] → Accepted, because #99
  defines the rule this way. The window is the span of the task's own sessions, which
  keeps overlaps rare. Each rejection records which task value caused it.
