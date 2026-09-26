---
status: "accepted"
date: 2026-09-26
decision-makers: ekolvah
---

# Releases go through release-please

## Context and Problem Statement

The plugin version lives in three places — `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json` and `VERSION` in `skills/agent-process/scripts/init.py` —
and no procedure moved them. The tag `v2.0.0` was set by hand, and further PRs merged under
the same version string, so one version named two contents. A dry run of release-please on
`main` parsed none of the commits since `v2.0.0`: squash commits carried the change name
(`install-activation-order (#200)`) and no Conventional Commit type.

## Considered Options

* release-please-action in manifest mode, with the PR title carrying the type
* semantic-release
* A bespoke bump script or version check

## Decision Outcome

Chosen: **release-please-action in manifest mode, with the PR title carrying the type.**

* `release-please-config.json` (release type `simple`, no component in the tag) names the
  three places as `extra-files`: the two JSON files by jsonpath, `init.py` through its
  `x-release-please-version` marker. `.release-please-manifest.json` holds the released
  version. `.github/workflows/release-please.yml` opens or updates one release PR on each
  push to `main`; merging it creates the tag `v<version>` and its GitHub Release.
* The workflow runs on a fine-grained PAT, secret `RELEASE_PLEASE_TOKEN`, scoped to this
  repository with Contents and Pull requests read/write. Events created with `GITHUB_TOKEN`
  start no workflow, so without it the required contexts would never run on the release PR.
  Only this publisher repository needs the token; consumer installation does not.
* The Deliver task titles every PR `<type>: <change>`. The repository squashes with
  `squash_merge_commit_title=PR_TITLE` and allows neither merge commits nor rebases, so that
  title is the commit release-please reads.
* `.github/workflows/pr-title.yml` runs `amannn/action-semantic-pull-request` on every opened,
  edited, pushed or reopened PR and fails a title without `feat`, `fix`, `docs`, `test`,
  `refactor` or `chore`. A ruleset of its own, `pr-title`, requires that context:
  `activate_protection` converges the context set of the process ruleset and would drop a
  foreign one, while rules of several rulesets on one branch aggregate.
* The release PR links its issue by hand: the person links it in the Development panel,
  requests `@codex review`, and merges.

### Native alternatives considered

* semantic-release — needs a Node release config and publishes on every merge, with no PR
  for the person to approve.
* A bespoke bump script or drift check — a standard tool exists
  ([ADR 0027](0027-v2-standards-replace-the-bespoke-control-plane.md)).
* A GitHub App token instead of the PAT — no expiry, but an App and two secrets for one
  repository.
* commitlint on branch commits — checks commits that the squash discards, not the title that
  lands on `main`.

### Consequences

* Good, because the three places move in one commit of one reviewed PR and cannot disagree.
* Good, because a PR without a type cannot merge, instead of silently missing the release.
* Bad, because the PAT expires and its date is the person's to track; an expired token shows
  as a red `release-please` run on the `main` commit.
* Bad, because a wrong but valid type (`docs` on a behaviour change) passes; the release PR's
  `CHANGELOG.md` shows the missing entry before the person merges.

### Cutting a release

1. Link the release's issue to the open release PR.
2. Comment `@codex review` on it.
3. Merge it once its checks are green; the tag and the GitHub Release follow.

### Deletion condition

* Remove the PAT when the GitHub App or a workflow-token route is adopted.
* Remove release-please if the plugin cache stops keying by version.
* Delete the `pr-title` ruleset before `pr-title.yml`: while it stands, a missing workflow
  blocks every PR into `main`.

### Confirmation

`tests/publisher/test_plugin.py::test_version_drift` holds every version place equal to the
manifest and the config naming each place;
`tests/publisher/test_reusable_workflows.py::test_pr_title_requires_a_conventional_commit_type`
holds the check's context, triggers and types.
