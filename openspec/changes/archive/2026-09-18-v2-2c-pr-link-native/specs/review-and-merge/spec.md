## ADDED Requirements

### Requirement: A PR links its issue
Every PR SHALL link at least one issue by GitHub's own link — a closing keyword in the
body, a manual link, or the branch `gh issue develop` created. A step of the `quality`
check SHALL read the PR's `closingIssuesReferences` once, with read access to pull
requests and issues, and SHALL fail the check when the list is empty, printing how to
link the issue and the command that re-runs the check; no check parses the branch name
or the PR body for the link, and no other check carries it.

#### Scenario: PR from a linked branch
- **WHEN** a PR is opened from a branch `gh issue develop` created for its issue, with no closing keyword in the body
- **THEN** the step reads the issue in `closingIssuesReferences` and the check goes on to the quality driver

#### Scenario: PR without an issue
- **WHEN** a PR links no issue
- **THEN** `quality` fails naming the two ways to link and `gh run rerun` of the run, and the driver's checks do not run

## MODIFIED Requirements

### Requirement: Required checks protect the default branch
The default branch SHALL require the checks `quality / quality` and `agent-review /
agent-review` from the reusable workflows. The required list is declared in the
repository; drift between the declared and the installed protection SHALL block a push
before `ci_check` runs.

#### Scenario: Missing required context
- **WHEN** an installed protection lacks a declared context
- **THEN** the pre-push hook reports drift and does not run `ci_check`

## REMOVED Requirements

### Requirement: An issue-branch PR links its issue
**Reason**: the check inferred the link from the branch name and the PR body; on a branch
named after its change it verified nothing, and GitHub's `closingIssuesReferences` is the
link itself. **Migration**: replaced by "A PR links its issue" above — every PR, read from
the platform's field by a step of `quality`; the `pr-link` workflows and the script are
deleted and the context leaves the protection.
