---
status: "accepted"
date: 2026-10-11
decision-makers: ekolvah
---

# Task telemetry follows the bound sessions

## Context and Problem Statement

[ADR 0037](0037-one-emitter-feeds-both-telemetry-backends.md) gives a task its identity
through the launcher `task_session.py`, which puts `task_id` and `attempt_id` on the
session's resource. The owner's sessions are started by the VS Code extension, not by the
launcher, so their telemetry has no `task_id`. The per-task readings found no token sample
for those tasks, and the dashboard showed only the one task that had been launched.

Observed on 2026-10-11:

* every Claude Code event in Loki carries the structured metadata `session_id`, and every
  `claude_code_token_usage_tokens_total` series carries the label `session_id`;
* that id equals the Claude Code session id, which a script reads as
  `CLAUDE_CODE_SESSION_ID`.

The owner works in two scenarios: discuss in chat, create the task, plan it, implement it,
merge; or start from an existing task at the plan. Chat may happen between the steps.

## Considered Options

* **Who binds a session to a task:** the delivery scripts that already know the issue; a
  `PostToolUse` hook parsing issue numbers out of Bash command lines; the launcher, as now.
* **Where the bindings live:** a ledger in the git common directory; a `sessions` file per
  change; a comment on the issue per binding.

## Decision Outcome

Chosen: **the delivery scripts bind the session to the issue in a ledger of the clone, the
archive exports the issue's sessions with the change, and the readings filter Grafana by
those session ids.**

* **Binding.** `create_tracking_issue`, `start_change` and `archive_change` call
  `session_binding.bind(issue)` with `CLAUDE_CODE_SESSION_ID`. Filing a side issue with
  `set_status --area` does not bind. A hook would have to guess the issue from arbitrary
  commands, and no standard tool links a session to an issue.
* **One session, one task.** A session already bound to another issue is refused with exit 2
  and `session <id> already leads issue-<A>; open a new session for issue-<B>`, before the
  script's first side effect. Pre-task chat counts when the same session runs the plan.
* **Ledger.** `<git common dir>/agent-process/sessions`, one line `<session-id> <issue>` per
  binding, shared by every worktree of the clone, untracked and never pruned. A file per
  change cannot see a binding of a change in another worktree or one already archived. An
  issue comment needs the network at every step, and its search lag makes the guard racy.
* **Export.** After its clean-worktree check, `archive_change` writes the issue's sessions
  into `openspec/changes/<change>/sessions`, which the archive commit carries to the
  readings in CI. A session that starts after the archive is not counted.
* **Readings.** `task_readings.py` matches `session_id=~"<a>|<b>"`. `start` is the earliest
  token sample of those sessions; a session with no sample is named in `gap`. The columns
  `attempt_id` and `unlaunched_events` leave the CSV, and rule 1 is dropped: the matcher
  excludes a parallel session by construction.
* **The launcher stays** for traces. It is the only route of a session's spans to Langfuse,
  where a problem that Grafana shows is analysed. Its `task_id` stays on the resource, but
  the readings no longer read it.

### Consequences

* Good, because a task done in the owner's real scenarios gets readings with no extra step.
* Good, because a session cannot be counted toward two tasks.
* Bad, because the readings depend on `CLAUDE_CODE_SESSION_ID`. Without it each script prints
  `session not bound`, and the task's row records `telemetry: no bound session`.
* Bad, because a fixer session started after the archive is not counted.
* Neutral: the owner's sessions still send no traces until a separate change sends traces
  from every session.

### Reconsider condition

* Claude Code renames `CLAUDE_CODE_SESSION_ID` or stops putting `session_id` on its events.
* A resumed session gets a new id without a binding script running in it.

### Confirmation

`tests/publisher/test_session_binding.py` covers the binding and the guard, and
`tests/agent_process/test_task_readings.py` the session filter. The `session_id` metadata and
label were observed live, because the ingest path is third-party.
