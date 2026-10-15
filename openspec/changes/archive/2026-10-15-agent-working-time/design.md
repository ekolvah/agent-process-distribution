## Context

See proposal.md (Why) for the readings and the observed metric. `task_readings.py` reads its
telemetry in `_telemetry`. One Prometheus query gives each bound session's first token sample,
and from those it takes `start` and the window `merged_at - start`. Loki queries over that
window give cost and counts. The dashboard is rendered from
`skills/agent-process/templates/per-task-dashboard.json`. Its "hours to merge" timeseries reads
`merged_at` and `hours` and adds a trailing mean `trend`.

## Goals / Non-Goals

**Goals:**

- One new column next to `hours`, from the same sessions and window as every telemetry reading.

**Non-Goals:**

- No split of the waiting time by cause (plan approval, review, merge approval). `hours` minus
  `agent_hours` is all of it.
- No trend line for `agent_hours`. The panel keeps its one `trend`, on `hours`.

## Decisions

### D1. The standard active-time metric, `type="cli"`

`agent_hours` reads `claude_code_active_time_seconds_total{type="cli"}` of the bound sessions.
Claude Code defines that value as tool execution and AI responses (proposal, Platform facts),
so it is the agent's time. `type="user"` (keyboard) is the person's time and is left out.

Alternatives:

- **PR timeline (last head to merge).** It measures only the wait after the PR opens and misses
  the wait for plan approval before `start_change`. It would also be a reading of our own where
  the vendor already exports one.
- **Sum of `duration_ms` of `api_request` and `tool_result` events in Loki.** The cost reading
  prefers events because a counter loses a reset's value. Here events do not fit: subagents and
  parallel tool calls overlap, so the sum can exceed wall time.

### D2. One query: per-series maxima of reset-free sessions

With `S` = `claude_code_active_time_seconds_total{session_id=~"<sessions>",
vcs_repository_name="<repo>",type="cli"}`, the one query at `merged_at` is:

```promql
sum by (session_id) (max_over_time(S[<window>s]))
  and on (session_id) (sum by (session_id) (resets(S[<window>s])) == 0)
```

A counter's maximum is its total while it does not reset. Summing the maxima counts a session
that has several series (proposal, PR 422). A reset would lose the value before it, so the
`and` drops that session. A session in `starts` that is missing from the answer leaves
`agent_hours` empty, with `agent_hours: no reset-free active time of <id>` in `gap`. That is the
existing gap mechanism with one cause string, like `telemetry: no token sample of <id>`.
Observed on 2026-10-15 over `[10d]`: for PR 419's session, PR 422's session and the reset
session `43b7bee7-…` the query returned 2769.872 and 2333.375, and nothing for the third.
`increase()` was rejected because it under-reports without a gap (proposal, Platform facts).
A reset loses the cell. That is accepted at the observed rate of 2 sessions in 99 over 14 days
(proposal, Platform facts). A bound session without a token sample is outside the window and
does not count, as for every telemetry reading.

### D3. Dashboard: two series on the existing panel

The hours panel's query adds the column `agent_hours` (number). The override that now names
`hours` "per task" names it "to merge", and a new override names `agent_hours` "agent
working". The title becomes "hours: to merge and agent working". The `isNull` filter stays on
`hours`, so a row with a `hours` value and an empty `agent_hours` draws a point for `hours`
only. In the table's `organize.indexByName`, `agent_hours` takes the index after `hours`, and
the later columns shift by one.

## Risks / Trade-offs

- [Active time is kept about 14 days in Prometheus, against 31 days for Loki events] → The same
  limit already applies to `start`. A PR recorded after that time has no `start` and no
  `agent_hours`.
- [A future Claude Code version renames `type` or its values] → The cell is then empty with a
  gap, never a silent 0 (D2).

## Migration Plan

The merge of this PR records its own row with the new script, because the caller runs the
callee at `main`. When the header is rewritten, earlier rows get an empty `agent_hours`. After
merge, a dispatch of `gh workflow run task-readings.yml -f pr=<N>` for PR 401–422 refills their
rows. It must run while their samples are still in Prometheus retention, until about
2026-10-25. The PR report names this step for the person, because the agent's run ends before
the merge. Rollback reverts the commit, and the header rewrite drops the extra column again. No
ADR: this design records the decision.
