## Context

`release-please.yml` runs on `push` to `main`: the action opens or updates the release PR, two
steps guarded by `prs_created` approve it (`GITHUB_TOKEN`) and enable auto-merge
(`RELEASE_PLEASE_TOKEN`), and a release created by the merge fast-forwards `stable`. The
ruleset "agent-process person approves" (read 2026-10-17) requires 1 approval with
`dismiss_stale_reviews_on_push: true`.

## Standard approach

- GitHub Actions `schedule`:
  https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
  — "Scheduled workflows run on the latest commit on the default branch."; "By default,
  scheduled workflows run in UTC."; "High load times include the start of every hour."; "If
  the load is sufficiently high enough, some queued jobs may be dropped."; "In a public
  repository, scheduled workflows are automatically disabled when no repository activity has
  occurred in 60 days."
- release-please-action input `skip-github-pull-request` — "if set to true, then do not try to
  open pull requests" (https://github.com/googleapis/release-please-action/blob/v4/action.yml);
  `src/index.ts` reads it with `core.getBooleanInput` and then skips
  `manifest.createPullRequests()`, whose result sets `prs_created` (`prs.length > 0`). The
  design follows it.
- release-please option `always-update` (16.15.0, "add `always-update` option to push to
  always push to release branch"; present in
  https://github.com/googleapis/release-please/blob/main/schemas/config.json; action v4.4.1
  depends on `release-please ^17.3.0`). Without it `maybeUpdateExistingPullRequest` in
  `src/manifest.ts` returns `undefined` when "If unchanged, no need to push updates"
  (`existing.body === pullRequest.body`). The design follows it.
- A merge queue addresses `strict` churn for all PRs and belongs to the separate re-review
  change.

## Goals / Non-Goals

**Goals:** at most one release-PR merge a day, outside the person's hours, keeping the
guard that only the run that produced the head approves it.

**Non-Goals:** skipping the re-review of a merge of `main`; a manual trigger
(`workflow_dispatch`) — nothing observed needs one.

## Decisions

1. **One workflow, PR work at night only.** `release-please.yml` triggers on `push` to `main`
   and on `schedule: cron "17 0 * * *"`; the action gets `skip-github-pull-request: ${{
   github.event_name == 'push' }}`. The approve and auto-merge steps stay as they are: a push
   run creates no PR, so `prs_created` is false and they skip. Rejected (the person chose,
   2026-10-17): the issue's shape, PR updated on every push plus a second nightly workflow that
   finds the PR, judges it with `release_pr.py` and approves it — more code, and it approves a
   head no run of its own produced. Minute 17 avoids the start-of-hour load; 00:17 UTC is
   03:17 at +03:00, and the person's commits on `main` over 2026-09-17..10-17 span 06:00–23:59
   local (`git log --date=format:%H`).
2. **`always-update: true`** in `release-please-config.json`. Without it a `docs`/`chore`
   merge after the day's last `feat`/`fix` leaves the release PR body unchanged, so it is not
   pushed, stays behind `main`, and `strict` blocks its auto-merge with a green run (would have
   happened on 2026-10-17: #455, #458 after #454). With it each nightly run pushes the PR onto
   the current `main`; the push dismisses the old approval and the same run approves again.
3. **Releases stay on every push.** `skip-github-release` is not set: the merge of the release
   PR at night starts a push run that creates the release and moves `stable`, as today.
4. **ADR 0047** records the cadence and amends ADR 0031 D4; ADR 0031 gets one "Amended by"
   line.

## Risks / Trade-offs

- [A scheduled run delayed or dropped by GitHub] → the PR is opened or merged the next night;
  no release is lost.
- [Checks red at night] → the PR stays open with auto-merge; the next nightly run pushes it
  again, which re-runs the checks and re-approves.
- [Unobserved: a run that updates a PR whose auto-merge is already on] → in the last 100
  release-please runs each release PR (#297..#457) got the approve and auto-merge steps once
  (`gh run list --workflow release-please.yml -L 100`, step conclusions), so neither
  `prs_created` on an update nor `gh pr merge --auto` on an enabled PR is observed. If either
  fails, the run fails red and the PR waits for the person; the first PR open past one night
  is the live check.
- [The 60-day disable] → unreleased commits on `main` imply recent activity.
- [Small gain] → the release-only merges of `main` were 2 of 20 extra review rounds; the
  general fix is the separate re-review change. The release PR's own daytime CI runs go too.

## Migration Plan

Merging this PR starts a push run that opens no release PR; the first nightly run opens the
release PR of this `feat` and merges it once its checks pass — the live check (approval by
`github-actions`, merge, tag, `stable`). No release PR is open on 2026-10-17 (`gh pr list
--head release-please--branches--main --state open` → `[]`). Rollback: revert the PR.
