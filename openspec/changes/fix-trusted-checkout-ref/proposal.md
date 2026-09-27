## Why

The trusted checkout in `reusable-agent-review.yml` and in `quality.yml` job `link` has never
checked out the pinned process commit. Both pass `ref: ${{ github.job_workflow_sha }}`. That
property does not exist: the contexts reference
(https://docs.github.com/en/actions/reference/workflows-and-actions/contexts) documents
`job.workflow_sha`, "The commit SHA of the workflow file that defines the current job", and no
`github.job_workflow_sha`. The runner confirms it is empty
(https://github.com/actions/runner/issues/2417). On an empty `ref`, `actions/checkout` falls
back to the event's ref, so `trusted/` holds the PR's merge commit.

Reproduction, run 36326501964 (`agent-review` on PR 225, head `f6cf02e`): the `with:` block of
`Checkout trusted review source` lists no `ref:`. The step then runs
`git checkout --progress --force refs/remotes/pull/225/merge`. The steps come from `main`, the
scripts from the PR, and `request_codex_review.py`, which the PR renamed, exits 2. The
successful run 36323480377 (PR 224) shows the same `refs/remotes/pull/224/merge` checkout, so
the fallback is not new. Nobody noticed it because the scripts on `main` and in the PR were
identical. Run 36326501841 (`agent-process`, PR 225) shows the same in job `link`.

Root cause: a wrong context property. The design of v2-2b assumed that an empty value fails the
checkout, but it falls back silently instead. Tracking issue 226.

## What Changes

- Both trusted checkouts take `ref: ${{ job.workflow_sha }}`.
- A step before each trusted checkout fails the job, naming the missing value, when
  `job.workflow_sha` is empty. The checkout never falls back to the PR's ref.
- ADR 0031 D2 names `job.workflow_sha`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: adds the requirement that the trusted checkout is the called workflow's
  commit, or the job fails.

## Impact

- Edited: `.github/workflows/reusable-agent-review.yml`, `.github/workflows/quality.yml`,
  `tests/publisher/test_reusable_workflows.py`,
  `.agent-process/docs/adr/0031-release-prs-merge-without-the-person.md`.
- Consumers get the fix with the next release that their `@v<version>` pins. The process
  scripts of a consumer's PR then stop feeding its own check. A consumer carries no process
  scripts in its PRs, so nothing that works today breaks.
- Unblocks PR 225. Once this is on `main`, the review of PR 225 runs `main`'s steps with `main`'s
  scripts.
