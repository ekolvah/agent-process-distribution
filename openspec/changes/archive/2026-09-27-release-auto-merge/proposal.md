## Why

After release-please landed (#201), it opens the release PR, and it stalls on the person (#203). Observed on the release PR
(#202) `chore(main): release 2.1.0`: `gh pr view 202 --json files` lists exactly
`.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `.release-please-manifest.json`,
`CHANGELOG.md`, `skills/agent-process/scripts/init.py`; `agent-process / quality` failed in 3 s
on "PR 202 links no issue"; `agent-review / agent-review` waited for a Codex review nobody
requested; the person merged. Each step re-gates content already reviewed and linked in the
`feat`/`fix` PRs the release collects, so fixes reach no one until the person remembers. ADR
0030 D4 kept these steps manual on purpose; this change replaces that decision.

The issue keys the exemption to the release-please file set. The set is not code-free:
`init.py` is code, and `plugin.json` declares the plugin's hooks. A file-set test alone would
let any change to those files skip the link and the review, so the release PR is recognised by
its diff: every changed file is in the set, and every one except the changelog equals its base
with the manifest's old version replaced by the new one.

Platform facts (read 2026-09-26):
- release-please-action README, Outputs: "`prs_created` — `true` if any pull request was
  created or updated"; "`pr` — A JSON string of the PullRequest object".
- GitHub docs, *Automatically merging a pull request*: "Before you use auto-merge, it must be
  enabled for the repository." and "Auto-merge is disabled if someone without write
  permissions pushes new changes to the head branch or switches the base branch."
- `gh api repos/ekolvah/agent-process-distribution` reads `allow_auto_merge: false`; ruleset
  `agent-process default branch` requires `agent-process / quality` and
  `agent-review / agent-review`, 0 approvals, strict status checks.

## What Changes

- New `.agent-process/scripts/release_pr.py`: reads the PR's base and head through the
  repository's `gh_io` boundary and publishes `release=true|false` as a step output (naming
  why when false); a failed read fails the step.
  It reads `release-please-config.json` and the manifest at the base, so a PR cannot widen
  the set it is judged by. A repository without that config has no release PR.
- `quality.yml`: the `link` job checks out the trusted process source at
  `github.job_workflow_sha`, runs `release_pr.py`, and skips the issue-link step on a release
  PR. `plan`, `check` and the gate are unchanged, so the tests still run.
- `reusable-agent-review.yml`: the same detection; on a release PR the Codex wait, the Claude
  fallback and its verification do not run; the P0/P1 enforcement still runs.
- `release-please.yml`: when the action created or updated a PR, enables auto-merge (squash)
  on it with the same PAT.
- The repository setting `allow_auto_merge` becomes `true` (the person, once).
- ADR 0031 records the decision and supersedes ADR 0030 D4 and its *Cutting a release*.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `review-and-merge`: a release PR is recognised by its diff; it is exempt from the issue link
  and from the review wait and fallback; merging it is the platform's, not the person's.
- `distribution`: the release workflow enables auto-merge on the release PR; the release merges
  without the person.

## Impact

- Added: `.agent-process/scripts/release_pr.py`, `tests/publisher/test_release_pr.py`,
  `.agent-process/docs/adr/0031-release-prs-merge-without-the-person.md`.
- Edited: `.github/workflows/quality.yml`, `.github/workflows/reusable-agent-review.yml`,
  `.github/workflows/release-please.yml`, `tests/publisher/test_reusable_workflows.py`,
  `.agent-process/docs/adr/0030-releases-go-through-release-please.md` (status line and pointer
  to 0031).
- Removed: none.
- Repository setting: `allow_auto_merge=true`.
- Consumers: they get the exemption with the release that ships `quality.yml` (called at
  `@v<version>`); without a `release-please-config.json` nothing changes for them.
- Once this lands, every merged `feat`/`fix` produces a release within minutes, without a pause
  for the person.
