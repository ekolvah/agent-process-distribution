# review-and-merge Specification

## Purpose
What reviews a PR, what blocks a merge, and how the default branch is protected from agent
mistakes.

## Requirements

### Requirement: Reviewer instructions name the simplicity triggers
The review contract SHALL be one file the Claude review job reads from the trusted checkout,
and SHALL name reinvented functionality and unnecessary complexity as findings, coupled to
the principles file.

#### Scenario: Contract and principles
- **WHEN** the review contract or the principles change
- **THEN** the simplicity triggers stay the same narrow set in both

### Requirement: Unresolved P0/P1 threads fail the review check
The last step of the review job SHALL fail the check while an unresolved review thread whose
first comment, by the Claude review job, carries `P0` or `P1` exists, printing the thread URLs;
it SHALL read only the label and the resolved state, reply to no thread, and SHALL pass on
`P2`/`P3` threads, resolved or not, and on threads of any other author. Conversation
resolution is not required on the default branch: a `P3` does not keep a PR from merging.

#### Scenario: Unresolved blocking thread
- **WHEN** a `P1` thread by the Claude review job is unresolved on the head
- **THEN** the check fails and names the thread's URL, and no reply is posted to it

#### Scenario: Advisory thread
- **WHEN** only `P2`/`P3` threads, or threads of another author, are unresolved
- **THEN** the check passes

#### Scenario: Blocking thread resolved
- **WHEN** the fixer resolves the `P0`/`P1` thread its push addressed
- **THEN** the next run of the check on that head passes

#### Scenario: Review event re-runs the check
- **WHEN** a review thread of the head is resolved after the check concluded on that head — a resolve has no event of its own, and a run another event starts is a required context of its own that leaves the `pull_request` run as it was
- **THEN** the check is re-run by the fixer's `resolve_review_thread --thread --reply-file`, whose `gh run rerun` of that `pull_request` run reads the resolved state; the caller follows pushes alone and the script posts the reply after the resolve

### Requirement: A PR links its issue
Every PR SHALL link at least one issue by GitHub's own link — a closing keyword in the
body, a manual link, or the branch `gh issue develop` created — except a release PR. A step
of the `quality` check SHALL read the PR's `closingIssuesReferences` once, with read access
to pull requests and issues, and SHALL fail the check when the list is empty, printing how to
link the issue and the command that re-runs the check; on a release PR the step SHALL not run
and the driver's checks SHALL run as on any PR. No check parses the branch name or the PR
body for the link, and no other check carries it.

#### Scenario: PR from a linked branch
- **WHEN** a PR is opened from a branch `gh issue develop` created for its issue, with no closing keyword in the body
- **THEN** the step reads the issue in `closingIssuesReferences` and the check goes on to the quality driver

#### Scenario: PR without an issue
- **WHEN** a PR links no issue
- **THEN** `quality` fails naming the two ways to link and `gh run rerun` of the run, and the driver's checks do not run

#### Scenario: Release PR without an issue
- **WHEN** a release PR links no issue
- **THEN** the link step does not run, the driver's checks run, and `quality` concludes on them

### Requirement: No local hook reads protection
No local hook SHALL read the installed branch protection or rulesets: a push is gated by
`ci_check` alone, and a merge by the ruleset that protection activation writes.

#### Scenario: Push reads no protection
- **WHEN** a branch is pushed through the pre-push hook
- **THEN** the hook runs `ci_check` and issues no read of branch protection or rulesets

### Requirement: A release PR is recognised by its diff
A PR SHALL count as a release PR only when the repository's `release-please-config.json` at
the PR's base exists, the release manifest's version changes between base and head, every
changed file is one the configuration names — an `extra-files` path of a package, the release
manifest or a package's changelog — and every changed file other than a changelog exists at
both base and head and equals its base with each old manifest version replaced by the new one.
The configuration and the manifest SHALL be read at the base, the files at the head the check
runs on, from the trusted process source at the ref the caller pinned; neither the branch name
nor the author decides. A PR that is not a release PR SHALL be told why in the check's log; a
failed read SHALL fail the check instead of deciding either way.

#### Scenario: Release PR
- **WHEN** a PR changes the version places the base configuration names, the manifest and the changelog, and each non-changelog file differs from its base only by the version
- **THEN** it is a release PR

#### Scenario: Other change in a version file
- **WHEN** a PR bumps the manifest and changes, in a file the configuration names, anything besides the version
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

### Requirement: Claude reviews every head
The review job SHALL read once whether a closing comment of the workflow token's login names
the current head, and when none does SHALL run the Claude Code action with the review
contract read from the trusted checkout of the process at the ref the caller pinned. The
action publishes findings as inline comments labelled `P0`–`P3` and closes every review with
one comment naming the reviewed head; that closing comment alone is its review — its inline
comments are review nodes an interrupted action leaves behind. After the action the job SHALL
read, within a bounded time, whether that closing comment exists, and fail the check when it
does not. The job leaves no review state, no evidence and no classification, and nobody
requests the review. On a release PR the job SHALL neither read nor run the Claude Code
action, and SHALL conclude on the enforcement of the threads.

#### Scenario: New head
- **WHEN** the job runs on a head that no closing comment names — including a head whose only closing comment names an older head
- **THEN** the Claude Code action runs with the trusted contract and leaves inline `P0`–`P3` comments and, last, the comment naming the head, and the job verifies that closing comment

#### Scenario: Silent action
- **WHEN** the action finishes without publishing the closing comment within the bounded time
- **THEN** the check fails

#### Scenario: Re-run on a reviewed head
- **WHEN** the head's run is re-run and a closing comment names the head
- **THEN** the Claude Code action does not run again, and the attempt concludes on the enforcement of the threads as they are

#### Scenario: Re-run on an interrupted review
- **WHEN** the head's run is re-run after its first attempt's action left inline comments on the head and no closing comment
- **THEN** the read finds no review and the Claude Code action reviews the head again

#### Scenario: Reader failure
- **WHEN** the read of the PR's comments fails instead of establishing presence or absence
- **THEN** the check fails without running the Claude Code action

#### Scenario: Head from a fork
- **WHEN** the PR head is in another repository, on any event
- **THEN** the run has started only on the person's approval (the repository requires it for every external contributor) and holds no secret but the read-only `GITHUB_TOKEN`, so the Claude Code action fails and with it the check: a fork PR is reviewed by a person

#### Scenario: Event other than a push
- **WHEN** a caller runs the job for an event that is not `pull_request`
- **THEN** it runs the same path — the read, the action on absence, the verification, the enforcement — so its conclusion derives from a review of the head

#### Scenario: Release PR review
- **WHEN** the job runs on a release PR
- **THEN** it reads no review, the Claude Code action does not run, and the check passes unless an unresolved `P0`/`P1` thread exists

### Requirement: Local safety in Claude Code
Push to the default branch, force push and `gh pr merge` SHALL be denied locally by the
deny-list of `.claude/settings.json`. Merging is the person's, except the release PR, which the
platform's auto-merge merges once its required checks pass.

#### Scenario: Push to main from Claude Code
- **WHEN** an agent runs `git push origin main`, `git push --force` or `gh pr merge` in Claude Code
- **THEN** the project's deny-list carries a rule that denies it

### Requirement: Only the fixer resolves a review-job thread
No workflow step or required check SHALL resolve or classify a review thread. A `P0`/`P1`
thread the fixer's push addressed is resolved by the fixer from its own session, thread by
thread; every other thread is answered and left to the person.

#### Scenario: Required check and threads
- **WHEN** the required check runs
- **THEN** every review thread keeps its resolved state and receives no classification reply

#### Scenario: Addressed finding of the review job
- **WHEN** the fixer resolves a thread it addressed
- **THEN** the resolve accepts a `P0`/`P1` thread raised by the Claude review job, refuses one raised by any other author, refuses one raised against the current head, and refuses a `P2`/`P3` thread

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
