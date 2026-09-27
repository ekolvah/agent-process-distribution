## ADDED Requirements

### Requirement: Trusted checkout is the called commit
Every checkout of the trusted process source SHALL check out this repository at the commit of
the called workflow definition. When that commit is not available to the job, the job SHALL
fail and name the missing value. It SHALL NOT check out the PR's ref instead.

#### Scenario: PR changes a process script
- **WHEN** a PR changes a script that the trusted source runs, and a caller pinned to another commit runs the check
- **THEN** the check runs the script at the pinned commit, not the PR's version

#### Scenario: Called commit unavailable
- **WHEN** the called workflow's commit is empty in the job
- **THEN** the job fails before the trusted checkout, and its log names the missing value
