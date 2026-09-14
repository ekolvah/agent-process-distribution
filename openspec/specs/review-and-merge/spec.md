# review-and-merge Specification

## Purpose
What reviews a PR, what blocks a merge, and how the default branch is protected from agent
mistakes.

## Requirements

### Requirement: Required checks protect the default branch
The default branch SHALL require the checks `quality / quality`, `pr-link / pr-link` and
`agent-review / agent-review` from the reusable workflows. The required list is declared in
the repository; drift between the declared and the installed protection SHALL block a push
before `ci_check` runs.

#### Scenario: Missing required context
- **WHEN** an installed protection lacks a declared context
- **THEN** the pre-push hook reports drift and does not run `ci_check`

### Requirement: Local safety on both carriers
Push to the default branch, force push and `gh pr merge` SHALL be denied locally on both
carriers: a deny-list in Claude Code, a pre-tool hook in Codex. Merging is the person's.

#### Scenario: Push to main from Codex
- **WHEN** an agent runs `git push origin main` in Codex
- **THEN** the pre-tool hook denies it with the repository-policy reason

### Requirement: An issue-branch PR links its issue
A PR from an `issue-N-*` branch SHALL carry `Closes #N`; the `pr-link` check verifies the
link. On any other branch (fork, Dependabot, manual) the check is N/A and passes.

#### Scenario: PR link check
- **WHEN** a PR from an `issue-N-*` branch is opened
- **THEN** `pr-link` verifies the closing reference with read access to issues

### Requirement: Codex reviews on the author's request, Claude is the fallback
The PR author SHALL request the Codex review; the review workflow waits for a Codex review
of the current head and runs the Claude review only when that evidence is absent or
invalid.

#### Scenario: Valid Codex review
- **WHEN** Codex has reviewed the current head
- **THEN** the Claude fallback does not run

#### Scenario: Stale Codex review
- **WHEN** the only Codex review is for an older head
- **THEN** it is not accepted as evidence

### Requirement: No automation resolves a review thread
No workflow step or required check SHALL resolve a review thread; only a person or the
fixing agent does, thread by thread.

#### Scenario: Required check and threads
- **WHEN** the required check runs
- **THEN** every review thread keeps its resolved state

### Requirement: Reviewer instructions name the simplicity triggers
The review contract SHALL name reinvented functionality and unnecessary complexity as
findings, coupled to the principles file.

#### Scenario: Contract and principles
- **WHEN** the review contract or the principles change
- **THEN** the simplicity triggers stay the same narrow set in both
