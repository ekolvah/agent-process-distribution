## Context

Issue 99 measures a task: one delivery attempt of an issue, identified as `task_id=issue-<N>`,
`attempt_id=<K>` by the ADR 0037 launcher. This change reads its two GitHub-side metrics:
time from start to merge beside the change size, and review rounds of the plan and the code.
The person chose the start source (the first Grafana sample) and the plan-round source (a
`round` field in the review). Observations, 2026-10-10:

- **Start.** `POST $GRAFANA_URL/api/datasources/proxy/uid/grafanacloud-prom/api/v1/query` with
  `Authorization: Bearer $GRAFANA_SERVICE_ACCOUNT_TOKEN`, `query=min(min_over_time(timestamp(claude_code_token_usage_tokens_total{task_id="issue-101",attempt_id="1"})[30d:1m]))`,
  `time=2026-10-10T16:19:44Z` returned HTTP 200 with
  `{"status":"success","data":{"resultType":"vector","result":[{"metric":{},"value":[1791649184,"1791644556.698"]}]}}`
  (`2026-10-10T15:02:36.698Z`, an exact sample time, not a step). The same query for
  `issue-999` returned `"result":[]`. `min(min_over_time(timestamp(claude_code_token_usage_tokens_total)[60d:10m]))`
  returned 2026-09-26T16:08:55Z: about 14 days of retention.
- **Non-task sessions.** `task_id` label values over 7 days: `issue-101` and `unassigned`.
  The second is a historical value, which also appears on series of another repository and on
  series with no repository. 16 series of the last day carry no `task_id`. None of them
  matches `task_id="issue-<N>"`.
- **PR.** The GraphQL timeline of issue 101 (`CONNECTED_EVENT`, `CROSS_REFERENCED_EVENT`) holds
  one `ConnectedEvent` with subject PR 382 and cross-references to PRs 102, 104, 180, 380 and
  382. `start_change` creates the connection through `gh issue develop <N> --name <change>`
  (`start_change.py:272`).
- **Code rounds.** `gh pr view 382 --json comments` holds three `github-actions` comments
  whose first line is `Reviewed head SHA: <sha>`, each with a distinct SHA. `head_review.py`
  posts no second comment for a re-run of a reviewed head (its docstring).
- **PR 382:** additions 922, deletions 76, created 15:36:00Z, merged 16:19:44Z, `mergeCommit.oid`
  `5de04c93…`, `headRefName` `one-emitter-task-telemetry`.
- **Archived review over GraphQL.** `repository.object(expression: "5de04c9:openspec/changes/archive")`
  as `Tree` listed the entry `2026-10-10-one-emitter-task-telemetry`, and
  `object(expression: "5de04c9:openspec/changes/archive/2026-10-10-one-emitter-task-telemetry/architect-review.json")`
  as `Blob` returned its `text`: verdict `approve`, no `round`.

## Goals / Non-Goals

**Goals:** one command reads both metrics for one task. Every value it cannot read shows up as
a gap. Non-task sessions never move the reading. A baseline is recorded before the source
expires.

**Non-Goals:** cost, failed/denied calls and compactions, together with the telemetry
window-rejection rules (the sibling issue). Aggregation across tasks. Dashboards.

## Decisions

### D1 — Start is the task's first token sample

The start is `min(min_over_time(timestamp(claude_code_token_usage_tokens_total{task_id="issue-<N>",attempt_id="<K>"})[30d:1m]))`.
It is evaluated at the read time: the range is longer than retention, so the earliest sample is
the same at any later instant, and D2 needs the start before it can choose the PR. Exact `=`
matchers on both labels keep every non-task session out (observation above). The range is
fixed at the observed 30 days, longer than retention. An empty result is the gap
`start: no token sample of issue-<N> attempt <K>` and leaves the hours null.

The alternatives were a launcher comment on the issue, which posts to GitHub on every launch,
and the plan commit of `start_change`, which leaves planning out of the metric. The person
chose this source.

**Failure modes:**

- Work done before the first launched session is invisible, so the start is too late. That
  is the ADR 0037 owner-supplied identity.
- The first sample lags the first request by up to one metric export interval.
- After retention the gap shows instead of a value.

### D2 — The task's PR is the merged PR connected to the issue

The candidates are the `ConnectedEvent` PRs of issue N that merged at or after the start, or
all merged connected PRs when the start is a gap. If there is none, the reading carries the
gap `merge: no merged PR connected to issue <N>`. If there is more than one, the script exits
2 listing their numbers: the attempt cannot be attributed, and the person decides.

The alternatives were the free-text `tracking issue` reference in the PR body (not enforced,
and cross-references also include unrelated PRs, observed) and `closingIssuesReferences`,
which the process never sets because its reports never use `Closes`.

### D3 — Size is the PR's additions plus deletions

The diff includes the plan artifacts under `openspec/changes/archive/`. They are part of the
task's work, so they stay.

### D4 — Code rounds are distinct reviewed heads

Code rounds count the distinct SHAs on the first line `Reviewed head SHA: <sha>` of the
`github-actions` comments on the PR. One round means no rework. A PR comment by anyone else
does not count.

The alternative, commits after the PR opened (the issue 99 baseline), counts commits
that no review saw. The delivery procedure's "round" is a reviewed head.

### D5 — Plan rounds are the archived review's `round`

The schema gains a required `round` (integer, minimum 1). Its description holds the whole rule,
because the reviewer adapter already reads the schema as its contract: 1 on the change's first
review, otherwise one more than the `round` of the file it replaces, a file without `round`
counting as 1 (a review written before this change).

The script reads `openspec/changes/archive/<date>-<head branch>/architect-review.json` at the
PR's merge commit with the GraphQL `object(expression:)` reads observed above, inside the
GitHub protocol D2 already uses: a `Tree` listing of the archive picks the entry ending in
`-<head branch>`, then a `Blob` read returns the file. The head branch is the change name,
because `start_change` names the branch. A review without `round`, or no archived change, is a
gap. A local `git show` was the other read; it needs the merge commit fetched and a third
protocol, for the same file.

The alternatives were a list of past verdicts in the file, which is a larger schema change
for one integer, and counting reviewer runs in transcripts, which is not deterministic.

**Failure mode:** the count is written by the reviewer subagent. A reviewer that ignores the
rule under-counts, and nothing catches it except reading the archived file in the PR diff.
This is accepted. A deterministic counter would need a write path outside the reviewer that
the propose run does not have.

### D6 — An owner script behind protocols

`.agent-process/scripts/task_metrics.py --issue N [--attempt K]`, `--attempt` defaults to 1,
like the launcher. It runs owner-side next to `task_session.py`. It is not distributed:
consumers have neither the Grafana tenant nor the launcher.

- **Protocols (§II).** `Prometheus.instant(expr) -> float | None` and a `GitHub` protocol
  (connected PRs of an issue with merge time, merge commit, head branch, additions, deletions;
  comment authors and bodies of a PR; the archived review text at a commit, D5). Tests use
  in-memory doubles. The real adapters use `urllib` (no new dependency) and `gh api graphql`
  with `encoding="utf-8"`.
- **Credentials (§VI).** `GRAFANA_URL` and `GRAFANA_SERVICE_ACCOUNT_TOKEN` are read at start.
  A missing one exits 2 naming the variable, never a value.
- **Output and exit codes (§IV).** One JSON object: `task_id`, `attempt_id`, `pr`, `start`,
  `merged`, `hours_to_merge`, `lines_changed`, `plan_rounds`, `code_rounds`, `gaps`. Exit 0
  when `gaps` is empty, 1 otherwise. Exit 2 on bad arguments, a missing credential, an
  ambiguous PR, or a failed read (HTTP error, `gh` non-zero), naming the cause.

**Problem it closes:** issue 383. No reading of either metric exists. By hand it takes a
Prometheus query and four GraphQL reads per task, and the start expires after about
14 days. **The standard for the job** is a Grafana dashboard panel or `gh` by hand. A panel
cannot join PR data without a GitHub datasource plugin, which is new host state. `gh` alone
has no start, and by hand nothing records the gap markers. The standard covers half the
reading at best, so the script is the smaller thing.

### D7 — The baseline lives in the setup doc

`telemetry-measurement-setup.md` gains a "Per-task readings" section: the command, the five
sources (D1–D5), the retention limit, and a table. Its first row is the baseline, the reading
of `issue-101` attempt 1. A later reading of any task is set beside it.

The baseline's caveat goes into that row: that task was first launched for the ADR 0037 gate,
after its planning had run without the launcher. The doc names tasks by their label values
(`task_id=issue-101`, `attempt_id=1`): the `no-issue-refs` pre-commit hook rejects issue and
PR numbers in `.agent-process/docs/` outside ADRs.

## Risks / Trade-offs

- **The baseline expires.** The issue 101 sample ages out around 2026-10-24. The baseline
  task runs right after the implementation. If it is too late, the row records the start gap
  rather than a guessed value.
- **Owner-supplied identity.** A wrong `--issue`/`--attempt` at launch moves the start to
  another task. Only D2's merge-after-start filter and the person reading the row catch it.
- **The reviewer writes the round.** See D5.

## Migration Plan

1. The schema changes in this PR. In a consumer, a change in flight
   whose review lacks `round` fails `start_change` validation, naming `round`. Running the
   review again writes it (D5: 2, the replaced file counting as 1).
2. Archived reviews are not validated again, so they stay as they are. The script reports
   their plan rounds as a gap.

**Rollback:** revert the PR. Reviews written in between carry `round`, which the old schema
(`additionalProperties: false`) rejects. A change in flight then needs its review run again.
