---
status: "accepted"
date: 2026-10-17
decision-makers: ekolvah
---

# Release PRs merge nightly

## Context and Problem Statement

The default branch requires `quality` and `agent-review` with strict status checks, so each
commit on `main` puts every open PR behind it and its next head is a merge of `main` that
`agent-review` reviews again. Under [ADR 0031](0031-release-prs-merge-without-the-person.md)
D4 the release PR opened by a feature's push merges minutes later (#454 at 11:31, release
3.28.0 at 11:34), so nearly every feature merge adds a second commit on `main`. On the 28 task
PRs of 2026-10-10..17, 8 of the 20 extra review rounds were merges of `main`; 2 brought only a
release commit and 3 more a release commit with a feature.

## Considered Options

* One workflow: a daily `schedule` run alone opens or updates the release PR
* The release PR updated on every push, plus a second nightly workflow that finds the PR,
  judges it with `release_pr.py` and approves it
* Keep the release PR merging after each push

## Decision Outcome

Chosen: **one workflow, release PR work at night only.**

* `release-please.yml` triggers on `push` to `main` and on `schedule: cron "17 0 * * *"`
  (03:17 at +03:00; the person's commits over 2026-09-17..10-17 span 06:00–23:59 local; minute
  17 avoids the start-of-hour load). The action gets
  `skip-github-pull-request: ${{ github.event_name == 'push' }}`, so a push run creates no PR,
  `prs_created` is false, and the approve and auto-merge steps skip.
* `skip-github-release` stays unset: the nightly merge of the release PR starts a push run that
  creates the release and moves `stable`.
* `release-please-config.json` sets `always-update: true`. Without it a `docs`/`chore` merge
  after the day's last `feat`/`fix` leaves the PR body unchanged, so release-please does not
  push it, the PR stays behind `main`, and strict checks block its auto-merge. With it each
  nightly run pushes the PR onto the current `main`, which dismisses the old approval, and the
  same run approves again.

### Consequences

* Good, because at most one release commit lands on `main` a day, outside the person's hours.
* Good, because the run that produced the release PR head is still the one that approves it.
* Bad, because consumers on `stable` get a release once a day instead of after each merge.
* Bad, because a scheduled run may be delayed or dropped by GitHub; the PR is then opened or
  merged the next night.
* Bad, because it is unobserved whether an update of a PR whose auto-merge is already on sets
  `prs_created` and lets `gh pr merge --auto` succeed; if not, the run fails red and the PR
  waits for the person.

### Pros and Cons of the Options

* Second nightly workflow — more code, and it approves a head no run of its own produced.
* Merge after each push — the merges of `main` this ADR removes.

### Deletion condition

Remove the schedule and the action input when a merge of `main` with an unchanged PR diff no
longer costs a review round, or when releases leave release-please.

### Confirmation

`tests/publisher/test_reusable_workflows.py::test_push_to_main` and
`::test_release_pr_behind_main` hold the trigger, the action input and `always-update`. The
first nightly run after this ADR is the live check: `github-actions` approves the release PR,
it merges, and the tag and `stable` follow.
