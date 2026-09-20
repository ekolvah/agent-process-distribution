## ADDED Requirements

### Requirement: A release tag matches the distributed version
The version in `.claude-plugin/plugin.json` and the marketplace entry SHALL match, and a
release SHALL use the tag `v<version>` on the default branch. The consumer caller and
Codex checkout SHALL pin that tag, and a change to distributed behavior SHALL bump the
version before release.

#### Scenario: Version drift
- **WHEN** the plugin manifest, marketplace entry, caller template, or release tag name different process versions
- **THEN** publisher validation fails before release
