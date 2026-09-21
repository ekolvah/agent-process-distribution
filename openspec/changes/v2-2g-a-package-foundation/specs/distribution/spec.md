## MODIFIED Requirements

### Requirement: This repository dogfoods its own process
This repository SHALL carry the same rendered payload a consumer currently receives and
SHALL expose and enable the shared Claude plugin/skill package that later distribution steps
will install. Repository sessions and publisher tests SHALL exercise the shared skill source,
its portable scripts, its OpenSpec rule pointers, and its package-version identity before a
consumer installation path is added. Repository-only settings and v1 process files SHALL NOT
be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its current consumer payload and delivery gates remain intact
