## MODIFIED Requirements

### Requirement: Releases go through release-please
A release SHALL be cut by `release-please` alone: on a push to `main` it SHALL open or
update one release PR whose version follows the Conventional Commit types on `main` since the
last release, and that PR SHALL move every version place — `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `VERSION` in `skills/agent-process/scripts/init.py` and
the release manifest — to that version in one commit. The release PR SHALL be opened with a
token whose events start workflows, so the required contexts run on it. The release workflow
SHALL enable auto-merge with squash on the PR it opened or updated, with the same token, and
the repository SHALL allow auto-merge; a failure to enable it SHALL fail the workflow run.
Merging the release PR SHALL create the tag `v<version>` and its GitHub Release; no person or
script sets a release tag by hand.

#### Scenario: Version places agree
- **WHEN** the tests run on any head, including a release PR's
- **THEN** every version place equals the version of the release manifest, and the release-please configuration names each place

#### Scenario: Release PR opened or updated
- **WHEN** the release workflow opens or updates the release PR
- **THEN** auto-merge with squash is enabled on that PR, or the workflow run fails

#### Scenario: Release PR merged
- **WHEN** the release PR of version `<version>` merges once its required checks pass
- **THEN** the tag `v<version>` and a GitHub Release of that tag exist on the merge commit
