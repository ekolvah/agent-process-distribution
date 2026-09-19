## Why

Step 2d of the v2 plan (issue 107) was split into three changes (ADR 0027, the `check_red`
entry); this is the second, `wait_for_pr` alone, tracked by issue 143 and re-planned on
2026-09-19 after `v2-2d-check-red-test` (PR 145) merged: `check_red` lost `--report`, and
issue 146 (nine review rounds on PR 145) asks a design that replaces an input to list the
failure modes of the new input and what the script stops proving.

`wait_for_pr.py` polls `gh pr view --json statusCheckRollup,headRefOid` every 30 s, sorts
the rollup into concluded/failed with rules of its own (`_concluded`, `_failed`, `_GREEN`,
`StatusContext` vs `CheckRun`), trusts a concluded rollup only on two identical consecutive
polls, and restarts on a new head. `gh pr checks <PR> --json name,bucket,link` is the
standard reading of a PR's checks — gh sorts every context into one of five buckets and
keeps the latest run per name — so the script's own sorting is a copy of it. The review
wait is not the script's: a running `agent-review` check is the pending review, its bounded
wait for Codex is `codex-timeout-seconds` of `reusable-agent-review.yml` (issue 111 item 8).

Observations the design rests on (gh 2.87.3, sources at tag `v2.87.3`, 2026-09-19):

- `pkg/cmd/pr/checks/checks.go`: an empty rollup is the error `no checks reported on the
  '<branch>' branch` (line 303), returned before the export (lines 184–186); `--json` writes
  the export and returns before the `Failed`/`Pending` exits (lines 189–191 precede
  248–252), so a `--json` read exits 0 on failed or pending checks and non-zero only on an
  error; `--json` with `--watch` is refused (line 81); the watch leaves on
  `counts.Pending == 0` (line 218) and on the empty-rollup error inside its loop (lines
  228–237), exit 1 either way. `api/query_builder.go` `RequiredStatusCheckRollupGraphQL`:
  `commits(last: 1)` — every read is of the PR's current head.
- `pkg/cmd/pr/checks/aggregate.go` lines 72–88: buckets `pass` (SUCCESS), `skipping`
  (SKIPPED, NEUTRAL), `fail` (ERROR, FAILURE, TIMED_OUT, ACTION_REQUIRED), `cancel`
  (CANCELLED), `pending` (everything else, STALE included); lines 96–120
  (`eliminateDuplicates`): the latest run per name.
- `gh pr checks --help`: `--watch`, `-i, --interval int` (default 10), `--fail-fast`,
  `--required`, `--json fields`. `gh pr checks 145 --json name,bucket,link,state` exited 0
  with `[{"bucket":"pass","link":"https://github.com/ekolvah/agent-process-distribution/actions/runs/35439380056/job/105889672593","name":"agent-review / agent-review","state":"SUCCESS"},{"bucket":"pass",…,"name":"quality / quality",…}]`.
- `gh pr view 137 --json statusCheckRollup` lists one `agent-review / agent-review` entry
  after the `gh run rerun 35262221116` of that head (ADR 0027, `v2-2b-push-only` entry): a
  rerun replaces the check run in the rollup, so a queued rerun is a `pending` bucket, not
  a duplicate behind a concluded one.
- The empty rollup after a push and the runs attaching one at a time are on record in the
  archived `v2-1a-delivery-scripts` design (`openspec/changes/archive/`).

## What Changes

- `wait_for_pr.py`: the loop reads `gh pr checks <PR> --json name,bucket,link` every 30 s
  until the head reports at least one check and none is `pending`, then reads the review
  threads (GraphQL, unchanged) and prints `failed:`/`unresolved:` lines. Deleted: the
  `gh pr view` poll with its own sorting of the rollup. Exit codes: 0 clean, 1 failed or
  unresolved, 2 `gh` itself failed (as today for every `gh` error), 3 timeout naming what
  was still awaited. *Amended at the review of PR 147:* the first draft also deleted the
  two-poll settling and the head comparison; both are back — a concluded set is trusted
  once two reads 30 s apart agree on it, on one head (`gh pr view --json headRefOid` read
  before the checks), and the threads are read on that head or the loop starts over
  (design.md D1, "What the script stops proving").
- `gh pr checks --watch` is considered and ruled out (design.md D1): the loop that must
  exist for the empty rollup does the watching at the same cadence.
- ADR 0027: the `wait_for_pr` row of "Native alternatives considered", its deletion
  condition, and an entry of the observations above.
- Tests and the delivery-flow paragraph of the architecture page follow. The `tasks` rule
  of `openspec/config.yaml` is untouched: it already names `wait_for_pr.py <PR>`.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `implementation`: "The implementing run ends only after checks and reviews" — the
  buckets are `gh pr checks`'s; a cancelled check is unresolved; a `gh` failure is exit 2,
  never a verdict; a timeout names what was awaited.

## Impact

Edited: `.agent-process/scripts/wait_for_pr.py`, `tests/publisher/test_delivery_scripts.py`,
`.agent-process/docs/architecture/agent-process.md`,
`.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
`openspec/specs/implementation/spec.md` (by the archive). Added: nothing. Removed: nothing.
One PR; its own review loop is the first live run of the rewritten script.
