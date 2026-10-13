## Context

`task-readings.yml` checks out `main` and the `task-readings` branch, then runs
`.agent-process/scripts/task_readings.py` with this repository's `GRAFANA_URL` variable and
`GRAFANA_SERVICE_ACCOUNT_TOKEN` secret. The script is repository-agnostic: it reads
`GITHUB_REPOSITORY`, filters every query on `vcs_repository_name`, and passes `--repo` to `gh`.
It imports `gh_io` and `head_review`, which `reusable-agent-review.yml` also runs from a
checkout of this repository at `job.workflow_sha` (`path: trusted`). That pattern is already in
production for every consumer: `github.repository` and `github.token` in the callee are the
caller's, and `job.workflow_sha` is the commit of the pinned callee.

## Goals / Non-Goals

**Goals:** a task PR merged in an adopter gets a row in the adopter's own
`task-readings.csv`, read from the adopter's own stack; `init` renders the caller and names
the credentials it cannot set.

**Non-Goals:** routing an adopter's rows to this repository or to `aqxk4q`; the adopter
dashboard template (separate issue); private adopters reading the CSV over
`raw.githubusercontent.com`; deleting a caller from a consumer that uninstalls; configurable
datasource UIDs (the script keeps Grafana Cloud's `grafanacloud-prom` and `grafanacloud-logs`;
another stack gets a `telemetry: Grafana query failed: …` gap until one is observed).

## Decisions

### D1 — The callee runs the script from the trusted checkout; the script does not move

`reusable-task-readings.yml` checks out the caller's default branch
(`github.event.repository.default_branch`), then this repository at
`job.workflow_sha` into `trusted/`, and runs `python trusted/.agent-process/scripts/task_readings.py`
from the caller's root. The script and its two imports stay in `.agent-process/scripts/`.
In a called workflow `github.event` is the caller's event: `reusable-agent-review.yml` reads
`github.event.pull_request.*` in production. `repository.default_branch` is part of the
`repository` object of every webhook payload, `workflow_dispatch` included, per GitHub's webhook
docs; it is not yet read in a run here, so the confirmation run proves it.

- Alternative: move them into the plugin's `skills/agent-process/scripts/`, as the issue's
  scope item 1 says. Rejected: the plugin is installed on the person's machine, not on the
  Actions runner, so the workflow would still check out this repository to reach it, and
  `head_review.py` would then live in two places or move under `reusable-agent-review.yml` too.
  ADR 0012 already settles that CI logic is referenced, not copied.
- The fallback import (`from gh_io import …`) resolves from the script's own directory, so a
  consumer's own `scripts/` package is never imported: `python <file>` puts the file's
  directory, not the working directory, first on `sys.path`.

### D2 — The caller passes the URL as an input and the token as a secret

The callee declares inputs `pr` (number, required) and `grafana_url` (string, not required)
and the secret `grafana_service_account_token` (not required). The caller passes
`${{ github.event.pull_request.number || inputs.pr }}`, `${{ vars.GRAFANA_URL }}` and
`${{ secrets.GRAFANA_SERVICE_ACCOUNT_TOKEN }}`. Passing the variable explicitly avoids depending
on which repository's `vars` a called workflow sees, a behaviour not observed here. Neither is
`required`: an unset value must reach the script, which writes the `telemetry: unset …` gap
row and exits 1 (`test_grafana_unreachable[unset-credential]` covers it today), instead of the
platform refusing the call with no row.

The merged-or-dispatched condition is the caller job's `if:`; the callee has no condition.

### D3 — The first run creates the `task-readings` branch

The record step replaces the second `actions/checkout`:
`git ls-remote --exit-code --heads origin task-readings`; exit 0 runs
`git fetch --depth 1 origin task-readings` and adds it as the worktree `readings`, exit 2 adds a detached worktree and `git switch --orphan task-readings`,
any other exit fails the run. `upsert` treats an absent CSV as an empty file, so the row is
written under the header. The second checkout guaranteed the CSV was tracked; on the orphan it
is not, and today's `diff --quiet` then `commit -am` would skip it without an error. So the
step runs `git -C readings add task-readings.csv` and commits and pushes
(`push origin HEAD:task-readings`) when `diff --cached --quiet` fails;
`test_first_record_creates_the_branch` runs that step and catches the loss.

Observed 2026-10-13 on git 2.45.1, in a `--depth 1` clone of a repository without the branch:
`ls-remote exit=2`; after `worktree add --detach` and `switch --orphan` the worktree holds only
`.git`; after commit and push, `ls-tree` of `task-readings` lists only `task-readings.csv` and
`rev-list --count` is `1`. Not observed: a `GITHUB_TOKEN` with `contents: write` creating a
branch by push. This repository's `task-readings` was created by the person and release-please
uses a PAT. kinozal's rulesets cover only `main` (`gh api repos/…/rulesets`, 2026-10-13), and a
refused push fails the step red, so the confirmation run proves it visibly.

- Alternative: a `manual` row naming the branch, as the issue's scope item 3 says. Rejected:
  it needs one more read in `init` and a branch-creation command the person runs, while the
  workflow creates the branch with the token it already holds. Two first runs racing both
  create an orphan; the later push is rejected and that run is red, as any concurrent write is
  today, and a dispatch re-records it.

### D4 — One `manual task-readings` row for the two credentials

No platform check catches an unset credential before a run (D2 keeps both optional), so
without the row the first sign is a red run after the first merged task. `_secret_set` becomes
one `_secret_names(t)` read shared by `review-secret` and this row, so the secret list is read
once and a failed read marks both rows `(cannot read: <reason>)`; the only new read is
`gh variable list --repo <repo> --json name`, which printed `[{"name":"GRAFANA_URL"}]` here
(gh 2.87.3, 2026-10-13). It is not gated on repository visibility:
recording works for a private repository; only the dashboard's raw read needs a public one.

### D5 — This repository calls the callee at `@main`

Its `task-readings.yml` is the template's caller with `@main` for `@v<version>` and no managed
header, as `agent-review.yml` is. `@main` makes `job.workflow_sha` the merged `main`, so the
merged script runs, as the current `ref: main` checkout does. The workflow file name stays, so
`gh workflow run task-readings.yml -f pr=<n>` and the existing branch keep working.

## Risks / Trade-offs

- Every adopter's merged task PR now runs the workflow; until the `manual task-readings` row is
  done each run is red with a gap row. That is the intended visible state (§IV).
- A consumer that already has its own `.github/workflows/task-readings.yml` without the managed
  header gets an `init` conflict, as for the other managed callers.
- Rollback: revert the PR. Consumers keep their caller pinned to an existing tag, which keeps
  working; `init` of a later release does not delete it.

## Confirmation

After the release and its installation in ekolvah/kinozal_scraper with the `manual
task-readings` row done, a merged task PR there gets a row in kinozal's `task-readings.csv` on
its `task-readings` branch with telemetry cells filled. This is observed after merge and
reported on the tracking issue; the delivery PR cannot prove it.
