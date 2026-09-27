## Context

See proposal.md, Why. Two trusted checkouts exist: step `Checkout trusted review source` of
`reusable-agent-review.yml`, which the caller reaches `@main`, and step
`Checkout trusted process source` of `quality.yml` job `link`, which the publisher reaches as
`./` and a consumer as `@v<version>`. Both run `release_pr.py` from `trusted/`. The review job
also runs the head-review reader, the Claude action's contract and
`check_blocking_review_threads.py` from it.

## Goals / Non-Goals

**Goals:** `trusted/` is the called workflow's commit, and an unresolved commit fails visibly.

**Non-Goals:** no caller input carries the ref, the hard-coded `repository:` stays, and no
OIDC token is read.

## Decisions

- **D1 — `job.workflow_sha`.** The platform documents it as the commit SHA of the workflow
  file that defines the current job (proposal, Why). For a reusable workflow that is the
  callee's commit: `main`'s head for `@main`, the tag's commit for `@v<version>`.
  *Alternatives:* an explicit caller input duplicates the `uses:` pin, and the two can drift.
  Reading the OIDC claim `job_workflow_sha` needs `id-token: write`, which
  `test_caller_permissions_are_a_superset_of_callee_permissions` forbids.
- **D2 — guard step before each trusted checkout.**
  `Require the called workflow commit` sets `env: SHA: ${{ job.workflow_sha }}`, and its `run`
  exits 1 with `::error::job.workflow_sha is empty; the trusted checkout would fall back to the
  PR's ref` when `SHA` is empty. `actions/checkout` treats an empty `ref` as "use the event's
  ref" (runs 36326501964, 36323480377), so the checkout cannot be the guard.
  *Alternative:* `ref: ${{ job.workflow_sha || 'missing' }}` fails on a nonexistent ref, but
  the error does not name the cause.
- **D3 — local call.** The publisher calls `quality.yml` as `./`, so there `job.workflow_sha`
  is the PR's own commit. This is unchanged behaviour: `test_publisher_driver_keeps_a_same_head_catcher`
  keeps `agent-review`, which is called `@main`, as the context the PR cannot change.

## Risks / Trade-offs

- [`job.workflow_sha` is also empty in practice] → D2 fails the job on the delivery PR itself:
  `agent-process / link` runs the PR's `quality.yml`. Task 4.3 reads that log for a non-empty
  `ref:`.
- [The review job's `@main` callee cannot be observed before merge] → the first run of
  `agent-review` after the merge is the observation. Its `Checkout trusted review source` must
  show `main`'s SHA, not `refs/remotes/pull/<N>/merge`. The re-run of PR 225 is that run, and
  task 4.5 reports it.

## Migration Plan

`fix:` → release-please releases it, and consumers get it by bumping their pin. Rollback is a
revert of the PR.
