## Context

See proposal.md — Why for the stalled #202 and the platform facts. Current state:
`quality.yml` job `link` runs one `gh pr view --json closingIssuesReferences` step before any
checkout; `reusable-agent-review.yml` checks out the trusted process source at
`github.job_workflow_sha` and runs `request_codex_review.py --wait` from it; `release-please.yml`
runs the action with `RELEASE_PLEASE_TOKEN` (Contents and Pull requests read/write) and nothing
else. ADR 0030 D4 chose to keep the release PR manual; its alternative was the exemption this
change adopts.

## Goals / Non-Goals

**Goals:** the release PR merges on green required checks with no step of the person; the
exemption cannot be used by a PR that changes anything but version strings and the changelog.

**Non-Goals:** delivery to consumer machines (#199); a pause between a `feat`/`fix` merge and its
release; consumer repositories adopting release-please.

## Decisions

**D1. The release PR is recognised by its diff, not by its file set, branch or author.**
`init.py` is code and `plugin.json` declares hooks, both in the release-please set, so a
file-set test would pass any edit of them. Rule (spec *A release PR is recognised by its
diff*): config and manifest at the base; the changed paths of `compare/<base>...<head>` all in
the set; the manifest's versions change; each non-changelog path has status `modified` and its
head text equals the base text with every `old → new` pair of the manifest applied. The
changelog is prose and free. A `init.py` that carried another string equal to the old version
would be rewritten by the substitution and not by release-please, so the PR is simply not
recognised and meets the normal gates — the failure direction is the stall of today, printed
with the file name.
*Alternatives:* branch `release-please--branches--main` or PR author — both are the person's
PAT identity or a name anyone with write can push; moving `VERSION` out of `init.py` into a
data file — still leaves `plugin.json`, and changes the Install layout for no gain over D1.

**D2. One script, run from the trusted source in both checks.** `.agent-process/scripts/release_pr.py
--repo --pr --base-sha --head-sha` (shas from the `pull_request` event) reads through
`gh_io.run_gh`, the repository's one `gh` boundary, and publishes `release=true|false` with
`gh_io.publish_step_output`, printing the reason when false; a `RuntimeError` of the read exits
2 and fails the step. The config's absence is read from the base root listing
(`contents/?ref=<base>`), not from a 404, so every failed call stays a failure. It runs from the
trusted checkout at `github.job_workflow_sha`: code in the PR's own worktree would judge the PR
that edits it. In the publisher `quality.yml` is reached by `./`, so the trusted ref is the PR
head — the same trust as the workflow file itself; in a consumer it is the pinned tag. The
`link` job gains that checkout; the test that held "no checkout in `link`" is narrowed to "no
checkout but the trusted source", and the link step still reads `closingIssuesReferences`
through the API alone.
*Alternatives:* inline `jq` in each workflow — two copies of the rule and no unit tests; a
separate `release` job that `link` needs — a skipped `link` is `skipped`, which the gate
refuses, so the gate would need a special case.

**D3. What stops proving, and the catcher reached.** The guards this drops on a release PR:
- *Issue link* — proves traceability to an issue. The release PR's content is version strings
  and a changelog whose entries name the `feat`/`fix` PRs, each linked by the `link` step on its
  own head. No catcher needed beyond `release_pr.py` in `link` on the release PR's head.
- *Review* — proves a reviewer read the diff. The catcher is `release_pr.py` in `agent-review`
  on the same head (only version substitutions pass) and `test_version_drift` in
  `agent-process / quality` `check` on that head (every place equals the manifest).
- *The person's merge* — proves a human saw the `CHANGELOG.md` before the tag; ADR 0030 named
  it the catcher of a wrong but valid type (`docs` on a behaviour change). After this change
  nothing catches that before the release; the release notes show the missing entry after it,
  and the next `fix` corrects it. Accepted: the type is set by the planner in a PR that was
  reviewed.

**D4. Auto-merge is enabled by the release workflow on every run that touched a PR.** Step
after the action, `if: steps.release.outputs.prs_created == 'true'`, `GH_TOKEN` =
`RELEASE_PLEASE_TOKEN`, `gh pr merge --auto --squash "$PR"` with `PR` =
`fromJSON(steps.release.outputs.pr).number`. Re-enabling on each update is idempotent and
survives any disable. An unset `pr` makes the expression or the command fail, so the run is
red instead of silent. The merge follows the same squash title rule as every PR
(`squash_merge_commit_title=PR_TITLE`). The local deny of `gh pr merge` binds agents, not this
workflow.
*Alternative:* a separate workflow on `pull_request` of the release branch — keyed to a branch
name and a second trigger for one command.

## Risks / Trade-offs

- [The auto-merge commit might start no `push` workflow, so no tag] → GitHub starts no workflow
  for events of `GITHUB_TOKEN`; auto-merge is enabled here with the PAT. The docs page on
  auto-merge (read 2026-09-26) does not say on whose behalf the merge is made, so this is
  unobserved. Its symptom is an absence, not a red run: a merged release PR with no
  `Release Please` run on its merge commit, and `gh release view v<version>` failing. Task 6.2
  makes that read the post-merge check; if it fails, the next push to `main` runs
  release-please, which creates the pending tag, and the gap goes to a follow-up issue.
- [PAT lacks the scope to enable auto-merge] → the step fails red on the first release PR; the
  fix is the token's permissions, recorded in ADR 0031.
- [Every `feat`/`fix` releases within minutes] → accepted by #203; consumers move only through
  #199's gate (release drift and a reinstall PR the person merges).
- [`strict` status checks and a release PR behind `main`] → release-please rebuilds the PR on
  every push to `main`, which re-runs the checks on a current head.

## Migration Plan

1. Merge this PR (the person). The change's own PR is not a release PR.
2. The person sets `allow_auto_merge=true`
   (`gh api -X PATCH repos/ekolvah/agent-process-distribution -F allow_auto_merge=true`);
   until then step D4 fails red on each release PR — visible, and the person can still merge.
3. Merging this `feat` makes release-please open the next release PR; its checks and auto-merge
   are the live verification.

Rollback: revert the PR and set `allow_auto_merge=false`; the release PR returns to the manual
steps of ADR 0030.
