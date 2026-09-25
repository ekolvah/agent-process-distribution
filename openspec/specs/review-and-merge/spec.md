# review-and-merge Specification

## Purpose
What reviews a PR, what blocks a merge, and how the default branch is protected from agent
mistakes.

## Requirements

### Requirement: Local safety on both carriers
Push to the default branch, force push and `gh pr merge` SHALL be denied locally on both
carriers: a deny-list in Claude Code, a pre-tool hook in Codex. Merging is the person's.

#### Scenario: Push to main from Codex
- **WHEN** an agent runs `git push origin main` in Codex
- **THEN** the pre-tool hook denies it with the repository-policy reason

### Requirement: Codex reviews on the author's request, Claude is the fallback
The PR author SHALL request the Codex review (`@codex review`, after the PR opens and after
every push; automatic reviews in the Codex app stay off). The review job SHALL wait a
bounded time for a review of the current head by a reviewer the check trusts — the Codex app
or the job's own login — read as present or absent, never parsed: a native review by the
Codex app on that head, or a reviewer's clean comment naming that head; an error or
usage-limit message from the app is absence — and SHALL run the Claude Code action with the
review contract read from the trusted checkout of the process at the ref the caller pinned
only when the wait ended absent. Each reviewer publishes findings as inline comments
labelled `P0`–`P3`; the Claude Code action closes every review with one comment naming the
reviewed head, and that closing comment alone is its review — its inline comments are
review nodes under the job's login an interrupted action leaves behind; the job leaves no
review state, no evidence and no classification.

#### Scenario: Valid Codex review
- **WHEN** Codex has reviewed the current head
- **THEN** the Claude fallback does not run

#### Scenario: Stale Codex review
- **WHEN** the only Codex review is for an older head
- **THEN** it is not accepted as evidence

#### Scenario: Codex review absent
- **WHEN** the wait ends without a review of the head by either trusted reviewer — none, or an error or limit message instead of one
- **THEN** the Claude Code action runs with the trusted contract and leaves inline `P0`–`P3` comments and, last, the comment naming the reviewed head; the job then reads whether that closing comment exists under the workflow token — a silent fallback fails the check

#### Scenario: Re-run on a fallback head
- **WHEN** the head's run is re-run after its first attempt fell back to Claude and the fallback's closing comment names the head
- **THEN** the wait returns on that comment, the Claude Code action does not run again, and the attempt concludes on the enforcement of the threads as they are

#### Scenario: Re-run on an interrupted fallback
- **WHEN** the head's run is re-run after its first attempt's action left inline comments on the head and no closing comment
- **THEN** the wait ends absent and the Claude Code action reviews the head again

#### Scenario: Reader failure
- **WHEN** the read of the PR's reviews fails instead of establishing presence or absence
- **THEN** the check fails without running the Claude action

#### Scenario: Head from a fork
- **WHEN** the PR head is in another repository and the wait ended absent, on any event
- **THEN** the run has started only on the person's approval (the repository requires it for every external contributor) and holds no secret but the read-only `GITHUB_TOKEN` — the platform withholds the rest on `pull_request_review` as on `pull_request` —, so the Claude action fails and with it the check: a fork PR is reviewed by Codex or by a person, never by the fallback

#### Scenario: Event other than a push
- **WHEN** a caller runs the job for an event that is not `pull_request`
- **THEN** it runs the same path — the wait, the fallback on absence, the verification, the enforcement — so its conclusion derives from a review of the head; a run that only enforced would pass a head without any review

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

### Requirement: Reviewer instructions name the simplicity triggers
The review contract SHALL be one file both reviewers read — Codex through the repository's
instructions file, Claude through the trusted checkout — and SHALL name reinvented
functionality and unnecessary complexity as findings, coupled to the principles file.

#### Scenario: Contract and principles
- **WHEN** the review contract or the principles change
- **THEN** the simplicity triggers stay the same narrow set in both

### Requirement: Unresolved P0/P1 threads fail the review check
The last step of the review job SHALL fail the check while an unresolved review thread whose
first comment, by either reviewer, carries `P0` or `P1` exists, printing the thread URLs; it
SHALL read only the label and the resolved state, reply to no thread, and SHALL pass on
`P2`/`P3` threads, resolved or not. Conversation resolution is not required on the default
branch: a `P3` does not keep a PR from merging.

#### Scenario: Unresolved blocking thread
- **WHEN** a `P1` thread by Codex or by the Claude review job is unresolved on the head
- **THEN** the check fails and names the thread's URL, and no reply is posted to it

#### Scenario: Advisory thread
- **WHEN** only `P2`/`P3` threads are unresolved
- **THEN** the check passes

#### Scenario: Blocking thread resolved
- **WHEN** the fixer resolves the `P0`/`P1` thread its push addressed
- **THEN** the next run of the check on that head passes

#### Scenario: Review event re-runs the check
- **WHEN** a review thread of the head is resolved after the check concluded on that head — a resolve has no event of its own, and a run another event starts is a required context of its own that leaves the `pull_request` run as it was
- **THEN** the check is re-run by the fixer's `resolve_review_thread --thread --reply-file`, whose `gh run rerun` of that `pull_request` run reads the resolved state; the caller follows pushes alone and the script posts the reply after the resolve

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

### Requirement: No local hook reads protection
No local hook SHALL read the installed branch protection or rulesets: a push is gated by
`ci_check` alone, and a merge by the ruleset that protection activation writes.

#### Scenario: Push reads no protection
- **WHEN** a branch is pushed through the pre-push hook
- **THEN** the hook runs `ci_check` and issues no read of branch protection or rulesets
