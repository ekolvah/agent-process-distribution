## Context

See proposal.md, Why, for the observations. The reads already exist. Setup document
"Per-task readings" holds the GitHub reads, "Per-task metrics" the Loki queries with the
zero-versus-missing rules, and dashboard `aqxk4q` the same queries filtered to this
repository. This change runs those reads once per merged task and keeps the result in git.

## Goals / Non-Goals

**Goals:** one row per delivered task that outlives Loki and Prometheus, readable on `aqxk4q`,
with an unreadable reading visible as a gap.

**Non-Goals:** Langfuse (issue scope), recording the rule-2 comparison (D4), and keeping the
dashboard JSON in git.

## Decisions

### D1. A CSV on the unprotected branch `task-readings`, read by Infinity

`task-readings.csv` holds one header line and one line per task PR. The dashboard reads
`https://raw.githubusercontent.com/ekolvah/agent-process-distribution/task-readings/task-readings.csv`
through `grafanacloud-infinity` (CSV parser). The proposal records a read of a raw `main`
file through that datasource.

Alternatives:

- Prometheus remote write. The free plan expires the samples with the raw telemetry
  (proposal), and CI would need a write credential.
- The file on `main`. A workflow cannot push there, because the ruleset requires a PR. A PR
  per merge doubles the person's merges.
- JSON instead of CSV. An append becomes a rewrite of the array, and the git diff of a
  reading is no longer one line.

### D2. A workflow on merge, chosen by the person

`.github/workflows/task-readings.yml` has two triggers:

- `pull_request: types: [closed]`
- `workflow_dispatch` with a `pr` input

The job guard is
`github.event_name == 'workflow_dispatch' || github.event.pull_request.merged`. A guard on
`merged` alone would skip every dispatch, and dispatch is the route of the Re-run scenario and
of the Migration fallback. The job has `permissions: contents: write, pull-requests: read`, and
no concurrency group: GitHub cancels a pending run of the group when another queues, so a row
would be lost with no red run. The job does these steps in order:

1. Check out `main` (`ref: main`), so the code that runs and the archived change are both
   merged code.
2. Check out `task-readings` into `readings/`.
3. Run `python .agent-process/scripts/task_readings.py --pr <n> --csv readings/task-readings.csv`
   and keep its exit code.
4. If the file changed, commit and push. A push rejected because another merge wrote first
   fails the run, and dispatching it again re-applies the upsert on the newer file. Two task
   merges within one run's minute are rare in this repository, so a retry loop is not worth
   its untested shell.
5. Exit with the script's code. A non-task PR leaves the file unchanged and exits 0, so its
   run succeeds. A gap row reaches the branch, and its run still ends red.

For a PR from a fork, the token is read-only and the secrets are absent, so no row is written
and the run is red. Such a PR is recorded by dispatching the workflow with its number.

**Why a script.** The problem it closes is issue 389's: telemetry readings expire and the GitHub
readings are on no dashboard. The earlier change kept the reads as documented commands because no
reading had yet needed to outlive retention. A workflow now has to run them unattended. The
standard tools each cover one side. The Grafana GitHub datasource reads PRs live, but it is not
installed, and it reads neither telemetry nor the review's `round`. A Loki or Prometheus
recording rule keeps the telemetry, but on the plan's retention. Nothing standard joins the two
sides under one key.

The alternative, a script that the next delivery runs, was rejected by the person. Its
readings lag until the next delivery and land in unrelated PRs.

### D3. The task comes from the merged tree

The change is the PR's head branch. That is the name `start_change` gives the branch, and
`archive_change` archives the change under the same name. The task is the directory
named exactly `YYYY-MM-DD-<change>` under `openspec/changes/archive/` on `main`. A glob
`*-<change>` would also match a change whose name ends in `-<change>`. If there is no such
directory, the PR is not a task (spec, Non-task PR).

`<N>` comes from the first match of `start_change._TOKEN`'s pattern, `tracking issue (<N>|\d+)`,
in the archived `tasks.md`. That is the Group 0 token of SKILL.md, Tasks, and the first token
decides, as in `start_change`. `closingIssuesReferences` is not used, because PR 380 lists two
issues there. The pattern is copied, not imported: `skills/agent-process/scripts` is a
hyphenated path, so it is not importable as a package, and a one-line pattern is cheaper than
a file-location import.

`attempt_id` and `start` come from one query (D4): the launcher writes the attempt nowhere else.

### D4. The readings are the documented reads, over the task's own window

| Column | Read |
| --- | --- |
| `attempt_id`, `start` | One PromQL query, the setup document's start query grouped by attempt: `min by (attempt_id) (min_over_time(timestamp(claude_code_token_usage_tokens_total{task_id="issue-<N>",vcs_repository_name="<owner>/<repo>"})[30d:1m]))` at `time=merged_at` (under the 768 h limit). The highest `attempt_id`, compared as an integer, is the row's, and its value is `start` |
| `merged_at`, `lines`, `code_rounds` | One `gh pr view <n> --json mergedAt,additions,deletions,headRefName,comments`; lines are additions plus deletions |
| `hours` | `merged_at − start`, two decimals |
| `code_rounds` | Distinct heads of the reviewer's comments, by `head_review._REVIEWED_HEAD` and `head_review._by_reviewer`, the review job's own marker contract |
| `plan_rounds` | `round` of the archived `architect-review.json`. A review archived before the field has none, and its count was never observed, so the cell is empty with `plan_rounds: review without round` in `gap` |
| `cost_usd`, `api_requests`, `failed`, `denied`, `compactions` | The two Loki queries of "Per-task metrics", as GET instant queries at `time=merged_at` over `[<merged_at − start>s]`. The cost query is filtered to `task_id`/`attempt_id`; the counts query is not, since it groups by them |
| `unlaunched_events` | The rule-1 count, read from the same counts result: rows whose `task_id` does not match `issue-[0-9]+` |

`failed`, `denied` and `compactions` follow the document's zero-versus-missing rules. A
count of 0 is written only when the field has been shown to exist. Otherwise the cell is
empty and the gap is named. Rule 2 needs Langfuse keys in CI and is not recorded. It is read
live within retention, as before. `unlaunched_events` is recorded so that a later reader can
still reject the window.

### D5. Gaps, failure and replacement

- `gap` is a `; `-joined list of `<reading>: <cause>` entries, one per cause. Readings that
  fail for one cause share an entry under the group name `telemetry`, for example
  `telemetry: no token sample of issue-384` or `compactions: no compaction row in retention`.
  The empty cells show which readings it covers.
- An empty cell is never `0`.
- A Grafana HTTP error, or an unset `GRAFANA_URL` or `GRAFANA_SERVICE_ACCOUNT_TOKEN`
  (checked first, §VI), puts every telemetry reading in the gap with the cause. The script
  still writes the row, then exits 1.
- A `gh` failure before the task is known raises (`gh_io.run_gh`), writes no row and turns
  the run red. Without the task there is no key.
- The write replaces any row with the same `pr` (spec, Re-run) and keeps the other rows in
  file order.

### D6. Boundaries (§II)

Two `typing.Protocol`s are injected into `main`:

- `GitHub`: PR fields and comments, backed by `run_gh`.
- `Grafana`: a PromQL query and a LogQL query, each returning the result vector, backed by
  `urllib.request` through the datasource proxy. Loki is called with GET (proposal) and
  Prometheus with POST, as the earlier change observed
  (`openspec/changes/archive/2026-10-10-per-task-delivery-metrics/design.md`, Start). Task 3.3
  checks that the token stored as the secret may query.

The tests use in-memory doubles and a `tmp_path` tree holding an archived change. No new
dependency.

### D7. One-time state, confirmed by the person

- The secret `GRAFANA_SERVICE_ACCOUNT_TOKEN`, a Viewer service account. Reusing the owner's
  existing token or minting one is the person's choice.
- The variable `GRAFANA_URL`.
- The branch `task-readings`, created as an orphan with the header line.
- The `aqxk4q` panels.

The first rows are a backfill. Before the PR, the script runs locally for the merged task PRs
382, 385 and 388, and their rows are pushed to `task-readings`. This verifies the live
queries and gives the panels data. After the merge, this change's own PR is recorded by the
workflow, which is the end-to-end check (Migration).

## Risks / Trade-offs

- [A task re-delivered under the same `attempt_id` sums both deliveries] → Its start is the
  first sample of that attempt. The setup document tells the owner to launch a re-delivery
  with a new `--attempt`.
- [Earlier attempts of a task get no row] → Accepted. A row is for the merged attempt, and an
  abandoned attempt has no merge.
- [raw.githubusercontent.com caches for a few minutes] → A new row shows on the dashboard
  minutes after the merge. That is fine for a trend.
- [A reading taken after the telemetry has expired is a gap] → Expected, and visible. The
  start comes from Prometheus, which holds about 14 to 16 days (the proposal's oldest sample).
  The events come from Loki, which holds 31 days. A late backfill therefore loses `start` and
  `hours` first.
- [The dashboard is host state] → The setup document names its UID, the CSV URL and the panel
  queries, so it can be rebuilt.

## Migration Plan

The repository gains the workflow on merge. The PR's own close runs it, and its row on
`task-readings` is the post-merge check. If the close event does not start it, dispatching
it with the PR number is the check. Both happen after the agent stops, so the plain-words
explanation gives the person the commands. The PR references the tracking issue without
`Closes`, so the issue stays open until the person has seen the row. To roll back, remove the workflow. The branch and
its data stay, and can be deleted by the person.
