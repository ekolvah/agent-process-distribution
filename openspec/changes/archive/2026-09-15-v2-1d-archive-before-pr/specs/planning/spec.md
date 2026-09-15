## MODIFIED Requirements

### Requirement: A behaviour change carries its spec delta
A PR that changes target behaviour SHALL carry the change's spec delta and SHALL archive
the change before the PR opens: `archive_change` runs `openspec archive <change>` once
`ci_check` is green, so the head the review reads is the archived one, and a fix after that
is a later commit on the same PR. So `openspec/specs/` on `main` is what is implemented and
no second PR is needed.

#### Scenario: Behaviour change
- **WHEN** a PR changes what the process does
- **THEN** the PR contains the delta and the archived change from its first head
