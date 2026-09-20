## MODIFIED Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
An installed consumer's quality job SHALL invoke the reusable workflow from this
repository at the immutable tag its caller pins. The publisher's own quality job SHALL
instead invoke its repository-local reusable workflow so the change that introduces or
updates that workflow can create a runnable check before its release tag exists. The
reusable workflow SHALL read the PR-to-issue link, run the caller's declared `setup` and
`test` commands against the PR worktree, and validate OpenSpec there. A consumer PR SHALL
NOT replace the reusable workflow implementation selected by the pinned ref. The
publisher's local workflow changes SHALL be inspected on the settled current head before
the person merges.

#### Scenario: Quality check on a PR
- **WHEN** the quality workflow runs for a consumer PR
- **THEN** its process-owned steps come from the immutable tagged reusable workflow and its caller-declared commands run against the PR head

#### Scenario: Quality check on the publisher PR
- **WHEN** this publisher changes the reusable quality workflow before the matching release tag exists
- **THEN** its caller uses the repository-local reusable workflow from the same PR head and GitHub creates the `quality / quality` job
