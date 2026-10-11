## Why

Of the five tasks merged on 2026-10-10 and 2026-10-11, one has telemetry readings. The other
four carry `telemetry: no token sample of issue-<N>` in `task-readings.csv`. Readings find a
task only through the `task_id` label, and only the launcher `task_session.py` sets it. The
owner works in the Claude Code VS Code extension, which starts `claude` itself, so no session
of the real workflow carries `task_id`.

Observed on 2026-10-11:

- **Every event carries the session.** In Loki, `sum by (session_id, query_source)` over the
  repository's `api_request` events returns a `session_id` on every row, launcher sessions or
  not. `Explore` subagent requests carry their parent session's id. In Prometheus,
  `count by (session_id, task_id) (claude_code_token_usage_tokens_total{vcs_repository_name=...})`
  returns `session_id` on every series.
- **The id is the Claude Code session id.** The Loki ids `01966537-…`, `39c2b968-…` and
  `43b7bee7-…` are the names of transcripts under
  `~/.claude/projects/…-claude-worktrees-one-emitter-task-telemetry/`.
- **A script can read the session id.** In the Bash tool of a VS Code extension session,
  `CLAUDE_CODE_SESSION_ID=a5a09290-c4c4-…` is set. That is the name of the session's own
  transcript `a5a09290-c4c4-4877-81de-8d5946461354.jsonl` (Claude Code 2.1.296).

The person's scenarios:

1. Discuss in chat, create the task, plan it, implement it, merge. Chat can come between the steps.
2. Start from an existing task: plan it, implement it, merge.

Neither scenario runs a launcher. The person decided that one session leads one task, and
that a second task needs a new session.

The empty dashboard on 2026-10-11 has a second, separate cause. VS Code started on
2026-09-28 with an `OTEL_*` environment that sends metrics and logs to the local Alloy, and
Alloy now accepts only traces. That is an owner restart, not a repository change, and it
is out of scope here.

## What Changes

- **A session binds to its task.** `create_tracking_issue`, `start_change` and
  `archive_change` record `CLAUDE_CODE_SESSION_ID` against the change's issue in a ledger that
  every worktree of the clone shares.
- **One session, one task.** A session already bound to another issue makes the script exit 2
  before it acts and ask for a new session.
- **The archive carries the task's sessions** in `openspec/changes/<change>/sessions`.
- **Readings follow the sessions.** `task_readings.py` filters Loki and Prometheus by those
  `session_id`s instead of `task_id`, and rule 1 goes.
- **BREAKING (CSV columns).** `attempt_id` and `unlaunched_events` leave `task-readings.csv`;
  a file with the old header is rewritten.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `measurement`: the row's columns, the telemetry source (bound sessions, not `task_id`), the
  no-telemetry gap, and the new session binding with its one-task guard.

## Impact

- Added: `skills/agent-process/scripts/session_binding.py`, `tests/publisher/test_session_binding.py`,
  `.agent-process/docs/adr/0038-task-telemetry-follows-the-bound-sessions.md`
- Edited: `skills/agent-process/scripts/create_tracking_issue.py`,
  `skills/agent-process/scripts/start_change.py`, `skills/agent-process/scripts/archive_change.py`,
  `.agent-process/scripts/task_readings.py`, `tests/agent_process/test_task_readings.py`,
  `tests/publisher/test_plugin.py`, `tests/publisher/test_start_change.py` (the moved-scripts sets),
  `tests/publisher/conftest.py` (clears the session variable),
  `.agent-process/docs/telemetry-measurement-setup.md`,
  `.agent-process/docs/adr/0037-one-emitter-feeds-both-telemetry-backends.md` (status line),
  `openspec/specs/measurement/spec.md` (through the archive)
- Removed: none. `task_session.py` stays as the trace route to Langfuse (design D6).
- Runtime: the branch `task-readings` gets the new CSV header on the first run after the merge.
