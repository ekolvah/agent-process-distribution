## Why

The default-branch ruleset requires `quality` and `agent-review` with
`strict_required_status_checks_policy: true`, so each commit on `main` puts every open PR
behind it and its next head is a merge of `main` that `agent-review` reviews again. The release
PR adds one such commit after nearly every feature merge: `release-please.yml` opens it on the
push of the feature, approves it and enables auto-merge in the same run, so it merges minutes
later (`git log`: #454 at 11:31:27, release 3.28.0 #457 at 11:34:23 +0300; #448 09:04:00,
#449 09:06:51). On the 28 task PRs of 2026-10-10..17, 8 of the 20 extra review rounds were
merges of `main`; 2 brought only a release commit (release 3.24.0 in #441, 3.28.0 in #455) and
3 more a release commit with a feature.

## What Changes

- `release-please.yml` gains a daily `schedule` at 00:17 UTC, outside the person's hours. Only
  that run opens or updates the release PR; its existing steps approve it and enable
  auto-merge. A push to `main` no longer touches the release PR; it still creates the release
  of a merged release PR and moves `stable`.
- `release-please-config.json` sets `always-update: true`, so the nightly run moves an open
  release PR onto the current `main` even when its release notes did not change.
- Consumers on `stable` get at most one release a day instead of one per feature merge.
- Departs from the issue's "keeps updating the release PR on every push": the person chose
  one workflow over a second nightly workflow (design decision 1).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: requirement "Releases go through release-please" — the release PR is opened
  and updated by the nightly run only, and kept on the current `main`.

## Impact

- Added: `.agent-process/docs/adr/0046-release-prs-merge-nightly.md`.
- Edited: `.github/workflows/release-please.yml` (trigger, one action input, header comment);
  `release-please-config.json` (`always-update`);
  `tests/publisher/test_reusable_workflows.py`;
  `.agent-process/docs/adr/0031-release-prs-merge-without-the-person.md` (an "Amended by" line
  in D4); `openspec/specs/distribution/spec.md` (by archive).
- Removed: nothing.
- Unchanged, checked: ADR 0040 (approval identity stays `GITHUB_TOKEN`), the `stable`
  requirement (the merge still starts the push run that creates the release), `README.md`
  (no release cadence stated). Re-reviewing a merge of `main` with an unchanged PR diff is a
  separate change.
