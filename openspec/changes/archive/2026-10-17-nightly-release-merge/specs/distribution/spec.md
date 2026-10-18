## MODIFIED Requirements

### Requirement: Releases go through release-please
A release SHALL be cut by `release-please` alone: a scheduled run once a day at 00:17 UTC SHALL
open or update one release PR whose version follows the Conventional Commit types on `main`
since the last release, and that PR SHALL move every version place — `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `VERSION` in `skills/agent-process/scripts/init.py` and
the release manifest — to that version in one commit. The scheduled run SHALL update an open
release PR onto the current `main` even when its release notes are unchanged. A run started
by a push to `main` SHALL neither open nor update the release PR. The release PR SHALL be
opened with a token whose events start workflows, so the required contexts run on it. The
release workflow SHALL approve the PR it opened or updated with the workflow's own
`GITHUB_TOKEN`, and then enable auto-merge with squash on it with the release token. The
repository SHALL allow auto-merge and allow GitHub Actions to approve pull requests; a failure
of either step SHALL fail the workflow run. A run that opens or updates no release PR SHALL
succeed without approving or enabling auto-merge.
Merging the release PR SHALL create the tag `v<version>` and its GitHub Release; no person or
script sets a release tag by hand.

#### Scenario: Version places agree
- **WHEN** the tests run on any head, including a release PR's
- **THEN** every version place equals the version of the release manifest, and the release-please configuration names each place

#### Scenario: Release PR opened or updated
- **WHEN** the scheduled run opens or updates the release PR
- **THEN** `github-actions` approves that PR and auto-merge with squash is enabled on it, or the workflow run fails

#### Scenario: No release PR change
- **WHEN** the release workflow runs and opens or updates no release PR
- **THEN** the workflow run succeeds and the approval and auto-merge steps are skipped

#### Scenario: Push to main
- **WHEN** a push to `main` starts the release workflow
- **THEN** the run opens or updates no release PR, so a feature merged during the day leaves the release PR as the last scheduled run left it

#### Scenario: Release PR behind main
- **WHEN** the scheduled run finds an open release PR whose release notes are unchanged while `main` moved
- **THEN** it updates that PR onto the current `main`, and the run approves it and enables auto-merge again

#### Scenario: Release PR merged
- **WHEN** the release PR of version `<version>` merges once its required checks pass
- **THEN** the tag `v<version>` and a GitHub Release of that tag exist on the merge commit
