## Context

`task_readings.py` finds a task's telemetry by `task_id="issue-<N>"`, its window by the first
token sample with that label, and rejects the window by rule 1 when another session of the
repository sent events without the launcher. Only `task_session.py` puts `task_id` on a
session. The observations that this design rests on are in the proposal's **Why**:
`session_id` on every Loki event and Prometheus series, equal to the Claude Code session id, and
readable by a script as `CLAUDE_CODE_SESSION_ID`.

## Goals / Non-Goals

**Goals:** readings for tasks done in the owner's real scenarios with no launcher and no
extra step, and one session per task enforced by a script.

**Non-Goals:**

- fixing the stale `OTEL_*` environment of the running VS Code (owner restart);
- the live Loki panels of dashboard `aqxk4q`, which group by `task_id` and so show launcher
  sessions only; the per-task view is the "Recorded readings" row, which reads the CSV;
- re-recording PRs merged before this change.

## Decisions

### D1. The delivery scripts bind at plan, implementation start and archive

`create_tracking_issue`, `start_change` and `archive_change` already know the change's issue.
Each reads `CLAUDE_CODE_SESSION_ID` and calls one shared module, `session_binding.py`.
`archive_change` takes the issue from `start_change.tracking_issue(tasks_md)`, as
`create_tracking_issue` does.

- **Not a hook:** a `PostToolUse` hook would have to parse the issue out of arbitrary Bash
  command lines. There is no standard tool that links a Claude Code session to a GitHub issue.
- **Not issue creation in chat:** `set_status <N> --area` does not bind. A bound session that
  files a side issue for the backlog would be refused, and filing an issue is not working on it.

Pre-task discussion counts when the same session runs the plan. A session that only created
the issue and ended stays unbound.

### D2. Ledger in the git common directory

The ledger is `<git rev-parse --git-common-dir>/agent-process/sessions`, with one line
`<session-id> <issue>` per binding. Every worktree of the clone shares it. It is untracked
and never pruned, because a line is about 45 bytes.

- **Path:** resolved through the injected `gh` runner, as `start_change.exclude_worktrees`
  resolves its path.
- **Read and append:** follow the same shape as `exclude_worktrees`.

`bind(issue)` reads the ledger:

- an absent session is appended;
- the same issue is a no-op;
- another issue raises, and the script exits 2 with
  `session <id> already leads issue-<A>; open a new session for issue-<B>`.

Rejected alternatives:

- **A `sessions` file per change:** it cannot see the binding of a change that lives in another
  worktree or is already archived, so the guard would miss it.
- **An issue comment per binding:** it needs a network call on each step and adds comments to
  the issue. Its search lag makes the guard racy.

### D3. Guard order: refuse before the first side effect, then bind

- **`create_tracking_issue`:** before `gh issue create`. If the token has no number and the
  session is bound to any issue, the bound issue is necessarily another one, so the script
  refuses before the issue exists. It binds the new number once it is written into `tasks.md`.
- **`start_change`:** directly after the `Planned` check, before the worktree prune.
- **`archive_change`:** after the lock check, before the clean-worktree check.

### D4. The archive exports the bindings

After its clean-worktree check, `archive_change` writes the issue's sessions from the ledger,
sorted, into `openspec/changes/<change>/sessions`. `openspec archive` moves the file with the
change, and `git add -A openspec` commits it. The readings run in CI, so this file is how the
sessions reach it. The clean-worktree check accepts this file besides `tasks.md`, so a re-run
after a failed `openspec archive` rewrites it instead of stopping on it.

A session that starts after the archive, such as a fixer session in a new chat, is not
exported, and its cost is not counted. The archive commit is the head that the review reads,
so a later export would move the reviewed head.

### D5. Readings filter by session

`task_readings.py` reads `sessions` of the archived change into the matcher
`session_id=~"<a>|<b>"`:

- **`start`:** the earliest of `min by (session_id) (min_over_time(timestamp(claude_code_token_usage_tokens_total{session_id=~…,vcs_repository_name=…})[30d:1m]))`.
  A bound session missing from that result is named in `gap` (`telemetry: no token sample of
  <id>`), so a task with one exporting session and one broken one is not recorded as complete.
- **Window:** from `start` to `merged_at`, as before.
- **Queries:** the cost and counts queries carry the same matcher. Counts group
  `by (event_name, success, decision)`, so `_count_cells` no longer filters by task.
- **Zero versus missing:** the rules are unchanged.
- **No file, or no id in it:** the gap is `telemetry: no bound session`, and Grafana is not
  queried.

`attempt_id` and `unlaunched_events` leave the columns. `upsert` rewrites a file whose header
differs: the shared columns keep their values.

Two guards change:

- **Rule 1 is dropped.** It proved that the window held only the task's sessions. The session
  matcher now makes that true by construction.
- **The task label is replaced by the session list.** The input moves from a label that the
  launcher set to a file that the delivery scripts write. The failure modes and their catchers:
  - **No `CLAUDE_CODE_SESSION_ID`** (another harness, or a renamed variable): each script prints
    `session not bound` while it runs. The task's readings run on merge writes
    `telemetry: no bound session` and ends red.
  - **A hand-edited `sessions`:** it is in the archive commit, so the PR review on that head
    sees the diff.
  - **An id with no telemetry** (export broken, as on 2026-10-11): the readings run on merge
    names that id in `gap` and ends red.

### D6. The launcher stays

`task_session.py` is the only route for traces to Langfuse, where a problem that Grafana
shows is analysed in detail. The owner's sessions do not run it, so today they send no trace.
Its `task_id` stays on its session's labels, but readings no longer read it. ADR 0038 records
the decision, and ADR 0037's status points to it. A separate change sends traces from every
session and retires the launcher there.

## Risks / Trade-offs

- **A resumed session may get a new id.** This was not observed. A new id binds again at its
  next binding script. If no binding script runs, its cost is not counted.

## Migration

- **Before implementing:** the owner fully restarts VS Code. Otherwise the implementing
  session's telemetry still does not reach Grafana, and this PR's own row records the gap of D5.
- **First readings run after the merge:** it rewrites the CSV header. Earlier rows keep their
  values.
- **Rollback:** revert the PR. The CSV then fails the old header check until the person
  restores the old header on `task-readings`.
