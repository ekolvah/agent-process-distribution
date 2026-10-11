## Why

#99 judges one task by its cost, its failed and denied tool calls, and its context
compactions. Since #382 ([ADR 0037](../../../../.agent-process/docs/adr/0037-one-emitter-feeds-both-telemetry-backends.md))
every telemetry event of a launched session carries `task_id` and `attempt_id`, but nothing
reads them per task yet, and the issue asks to confirm how the inputs appear before they
are used. Observed on 2026-10-10 in Loki (`{service_name="claude-code"}`, this repository,
last 7 days, Claude Code 2.1.294–2.1.296):

- **Denials.** A denied call is a `tool_decision` event with `decision="reject"`:
  `source="hook"` 17, `source="config"` 6, no `source="user"` in the week (sessions run in
  auto mode). A rejected call emits no `tool_result`: 780 `accept` decisions, 780
  `tool_result` events. Failures are `tool_result` with `success="false"` and an
  `error_type` (`ShellError` 3, `TelemetrySafeError` 12).
- **Cost and cache TTL.** One `api_request` (model `claude-opus-5-5`; 2 input, 4 output,
  23 371 cache-read and 25 668 cache-creation tokens) has `cost_usd` 0.2101062. At $4 / $20
  per MTok, $0.20 cache read and the 1-hour cache write at 2× input ($8), the sum is exactly
  0.2101062; at the 5-minute rate ($5) it would be 0.1331. `cost_usd` prices the 1-hour TTL
  in use.
- **Compactions.** A `compaction` event carries `trigger`, `pre_tokens`, `post_tokens` and
  `success`.
- **Source.** All three `issue-101` gate sessions carry `task_id`. Their `cost_usd` sums
  over `api_request` events are 0.2805674, 0.4701438 and 0.4452932, which total 1.1960044.
  For the first two sessions, the sum equals `claude_code_cost_usage_USD_total`. The third
  is the first gate session, resumed before `service.instance.id` existed, and there the
  counter shows 0.3998: the counter reset hid a process. The events do not depend on
  counter continuity.
- **Gap.** No event with `terminal_type="vscode"` has arrived since 2026-10-09 05:12 UTC.
  The VS Code extension sessions of this repository export nothing, and the launcher sets a
  task identity only for a CLI session. No task has been measured yet: only the `issue-101`
  gate sessions carry `task_id`.

## What Changes

- The owner-side measurement setup document gains a per-task metrics section. It holds
  the LogQL queries for the three metrics, keyed by `task_id` and `attempt_id`, the
  observations above, the two window-rejection rules handed over on #99. Rule 1 replaces the document's current
  unlaunched-series sentence, and rule 2 extends its per-session totals check to a task.
- No baseline is recorded (owner's decision, 2026-10-11): the metrics are tracked across
  later tasks as skills are switched on and off. Task sessions are started through the CLI
  launcher. This change closes #384.
- Out of scope: restoring the VS Code export, and a task identity for VS Code sessions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true`: the queries and the document are owner-side
measurement procedure, not process behaviour. No consumer receives them.

## Impact

- Edited: `.agent-process/docs/telemetry-measurement-setup.md`.
- Added, removed: none in the tree.
- Owner host: no change.
