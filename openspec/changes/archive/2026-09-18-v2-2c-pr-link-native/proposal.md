## Why

The PR → issue link is enforced by a third reusable workflow (`reusable-pr-link.yml`, its
caller `pr-link.yml`, the required context `pr-link / pr-link`) driving a 336-line script
(`verify_pr_link.py`) that GitHub's own field already answers — and since v2-1 that gate
has verified nothing. Observed (2026-09-18, this repository):

- The link needs no keyword. `gh pr view <PR> --json closingIssuesReferences` on the PRs
  opened from `gh issue develop` branches: PR 141 → `[138]`, PR 140 → `[139]`, PR 136 →
  `[130]`, PR 135 → `[134]`, PR 133 → `[129]`; none of their bodies carries `Closes #N`
  (PR 137, on the v1 branch `issue-130-review-events`, carried one and lists `[130]`). The
  linked branch is the link.
- The link precedes the check. PR 141 was created at `15:31:31Z`; the `connected` event on
  issue 138 (`gh api repos/…/issues/138/timeline`) is at `15:31:34Z`; the first `pr-link`
  run of the head, `35362952165`, was created at `15:31:36Z` and its verify step started at
  `15:31:45Z`. PR 140: created `05:47:00Z`, connected `05:47:01Z`, run `35312165283`, step
  at `05:47:15Z`. The field is computed within seconds of the PR and read ten seconds
  later; the 12 × 4 s poll of `verify_pr_link` guards a race that is not there.
- The gate is inert on v2 branches. `issue_number_from_branch` matches `issue-N-` alone;
  a branch named after its change returns `None`, the script makes no `gh` call and prints
  `ok: PR link check passed for branch 'observe-platform-facts'` (run `35364647176`) —
  the fact ADR 0027 records for the v2-1 run, true of every v2 PR since.
- The protection is classic (`gh api repos/…/branches/main/protection`: `strict: true`,
  checks `quality / quality`, `pr-link / pr-link`, `agent-review / agent-review`;
  `gh api repos/…/rulesets` → `[]`).

Root cause: the check was built when the link was inferred from the branch name and the PR
body; GitHub's `closingIssuesReferences` (closing keyword, manual link, or the branch of
`gh issue develop`) is the fact the check wanted, readable in one line.

## What Changes

- `.github/workflows/reusable-quality.yml`: one step before the trusted driver runs —
  `gh pr view "$PR" --json closingIssuesReferences --jq '.closingIssuesReferences | length'`
  non-zero, else `::error::` naming how to link (`Closes #N` in the body or a branch from
  `gh issue develop -c <N>`) and the re-run (`gh run rerun $GITHUB_RUN_ID`), exit 1. The
  callee and its caller `ci.yml` gain `pull-requests: read` and `issues: read` — the
  permission set the retired workflow ran with.
- **Removed**: `.github/workflows/pr-link.yml`, `.github/workflows/reusable-pr-link.yml`,
  `.agent-process/scripts/verify_pr_link.py`, the `verify_pr_link` tests of
  `tests/publisher/test_deferred_scope.py` and the `pr-link` tests of
  `tests/publisher/test_reusable_workflows.py`. The `## Deferred scope` soundness
  verification goes with the script: its consumer, the review downgrade, left the contract
  in `v2-2b`; the block `open_pr.py` still renders is inert until `v2-4` (issue 114)
  deletes the v1 scripts.
- `REQUIRED_CONTEXTS` of `.agent-process/scripts/check_branch_protection.py`: two
  contexts, `quality / quality` and `agent-review / agent-review`. The live protection
  drops `pr-link / pr-link` by one `gh api` call once this PR's checks are green (the
  context never reports on a PR that deletes its caller) — the person's, or the
  implementer's after their confirmation; the order is in `design.md`.
- Two reusable workflows stay (owner's decision, 2026-09-18, against the one-file plan of
  issue 131): a caller pins its callee `@main`, so a new callee file costs a PR of its own
  before a caller can name it, and one caller renames every required context; `init`
  (issue 112) writes the consumer's callers and is where one file is worth that.
- Docs: `agent-process.md` (Issue contract: the export is inert, nothing verifies it),
  `agent-process-installation.md` (two callers, two contexts), ADR 0027 (the observations
  above, what is deleted, ADR 0020 in the superseded list), `copier-answers.yml` (two
  lines of the dead Copier record).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `review-and-merge`: "Required checks protect the default branch" — two contexts;
  "An issue-branch PR links its issue" renamed to "A PR links its issue" — every PR SHALL
  link an issue by GitHub's `closingIssuesReferences`, read once by a step of the quality
  check; a missing link fails `quality` and prints how to link and how to re-run.

## Impact

- Edited: `.github/workflows/reusable-quality.yml`, `.github/workflows/ci.yml`,
  `.agent-process/scripts/check_branch_protection.py`,
  `tests/publisher/test_reusable_workflows.py`, `tests/publisher/test_deferred_scope.py`,
  `tests/agent_process/test_branch_protection.py`, `openspec/specs/review-and-merge/spec.md`
  (via this change's delta, applied by the archive),
  `.agent-process/docs/architecture/agent-process.md`,
  `.agent-process/docs/architecture/agent-process-installation.md`,
  `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`,
  `.agent-process/copier-answers.yml`; `.agent-process/scripts/open_pr.py` (one comment
  names the deleted sibling).
- Removed: `.github/workflows/pr-link.yml`, `.github/workflows/reusable-pr-link.yml`,
  `.agent-process/scripts/verify_pr_link.py`.
- Added: none. No new script: the check is one `gh` line of the callee.
- Outside the repository: the classic protection of `main` loses one context. The PR of
  this change runs the callee pinned `@main` — the step is first exercised on the PR after
  the merge; a PR without an issue then fails `quality`. No Dependabot or other bot opens
  PRs here today; an exemption is added when such a PR is observed, not before.
- Not touched: the rendering of `open_pr.py`, `update_pr_body.py`, `check_orphan_scope.py`
  and their tests, `.github/pull_request_template.md` (v1, deleted or rewritten by
  issue 112 / issue 114).
