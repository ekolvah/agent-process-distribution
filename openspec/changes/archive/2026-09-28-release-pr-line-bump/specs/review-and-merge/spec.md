## MODIFIED Requirements

### Requirement: A release PR is recognised by its diff
A PR SHALL count as a release PR only when the repository's `release-please-config.json` at
the PR's base exists, the release manifest's version changes between base and head, every
changed file is one the configuration names — an `extra-files` path of a package, the release
manifest or a package's changelog — and every changed file other than a changelog exists at
both base and head, has as many lines as its base, and each of its lines equals the base line or
the base line with each old manifest version replaced by the new one.
The configuration and the manifest SHALL be read at the base, the files at the head the check
runs on, from the trusted process source at the ref the caller pinned; neither the branch name
nor the author decides. A PR that is not a release PR SHALL be told why in the check's log; a
failed read SHALL fail the check instead of deciding either way.

#### Scenario: Release PR
- **WHEN** a PR changes the version places the base configuration names, the manifest and the changelog, and each non-changelog file differs from its base only by the version
- **THEN** it is a release PR

#### Scenario: Old version kept elsewhere
- **WHEN** a release PR bumps the version line of a file the configuration names and another line of that file keeps the old version, such as a comment
- **THEN** it is a release PR

#### Scenario: Other change in a version file
- **WHEN** a PR bumps the manifest and, in a file the configuration names, changes a line other than by the version, or adds or removes a line
- **THEN** it is not a release PR, and the log names that file

#### Scenario: File outside the set
- **WHEN** a PR bumps the manifest and changes a file the base configuration does not name, including the configuration itself
- **THEN** it is not a release PR, and the log names that file

#### Scenario: No release configuration
- **WHEN** the base has no `release-please-config.json`
- **THEN** no PR of the repository is a release PR

#### Scenario: Failed read
- **WHEN** the read of the base, the head or a file fails
- **THEN** the check fails with the read error
