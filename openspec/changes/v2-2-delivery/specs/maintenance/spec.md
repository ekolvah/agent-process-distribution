## ADDED Requirements

### Requirement: Versioning by tag
Plugin version and git tag `vN` SHALL version the process; reusable workflows are pinned by
tag in consumers; a breaking change is a major tag with a migration note.

#### Scenario: Breaking change
- **WHEN** a breaking change is released
- **THEN** consumers on the previous major tag are unaffected until they bump
