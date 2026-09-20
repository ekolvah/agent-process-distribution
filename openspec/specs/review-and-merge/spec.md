# review-and-merge Specification

## Purpose
What reviews a PR, what blocks a merge, and how the default branch is protected from agent
mistakes.

## Requirements

### Requirement: Required checks protect the default branch
The installed repository ruleset SHALL require the head-bound `quality / quality` context
from the pinned reusable workflow and require branches to be current before merging. The
required context SHALL be bound by name and the GitHub Actions integration, not by a
consumer-editable assertion that authenticates the caller file. The person SHALL inspect
every `.github/workflows/**` diff on the current PR head before merge; repositories that
can use organization-level required workflows MAY add that stronger external trust anchor.

#### Scenario: Missing required context
- **WHEN** the PR head has no successful `quality / quality` context
- **THEN** the ruleset blocks the merge

### Requirement: No automation resolves a review thread
No workflow step or required check SHALL resolve or classify a review thread. A `P0`/`P1`
thread the fixer's push addressed is resolved by the fixer from its own session, thread by
thread, whichever app raised it; every other thread is answered and left to the person.

#### Scenario: Required check and threads
- **WHEN** the required check runs
- **THEN** every review thread keeps its resolved state and receives no classification reply

#### Scenario: Addressed finding of either reviewer
- **WHEN** the fixer resolves a thread it addressed
- **THEN** the resolve accepts a `P0`/`P1` thread raised by the Codex app or by the Claude review job, refuses one raised against the current head, and refuses a `P2`/`P3` thread

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

### Requirement: The ruleset blocks unsafe default-branch updates
The installed repository ruleset SHALL require a pull request, block deletion, and block
non-fast-forward updates for the default branch. It SHALL have no process bypass actor.

#### Scenario: Direct default-branch update
- **WHEN** an actor without an external administrative bypass tries to update the default branch outside a qualifying pull request
- **THEN** GitHub rejects the update under the installed ruleset

### Requirement: Official review apps are advisory
The thin caller SHALL invoke `anthropics/claude-code-action@v1` directly for PR review, and
`init` SHALL print the instruction for the person to enable Codex automatic reviews. The
process SHALL NOT install a reusable review workflow, request Codex by comment, parse either
reviewer's output, or make a review result a required status check. Review comments and
threads SHALL remain visible for the agent and person to address; the person decides
whether the PR may merge.

#### Scenario: Pull request review
- **WHEN** a pull request opens or its head changes after installation is complete
- **THEN** the caller starts the Claude action and the person's Codex app setting independently requests the official reviews without a process parser or fallback

#### Scenario: Review unavailable
- **WHEN** either review app is unavailable or fails to publish
- **THEN** the absence or failed review job stays visible and does not masquerade as a clean process verdict
