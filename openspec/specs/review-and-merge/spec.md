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
The PR author SHALL request the Codex review (`@codex review`, after the PR opens and after
every push; automatic reviews in the Codex app stay off). The review job SHALL wait a
bounded time for a review of the current head by a reviewer the check trusts — the Codex app
or the job's own login — read as present or absent, never parsed: a native review by that
reviewer on that head, or its clean comment naming that head; an error or usage-limit
message from the app is absence — and SHALL run the Claude Code action with the review
contract read from the trusted checkout of the process at the ref the caller pinned only when
the wait ended absent. Each reviewer publishes findings as inline comments labelled
`P0`–`P3` and names the reviewed head when it finds nothing; the job leaves no review state,
no evidence and no classification.

#### Scenario: Valid Codex review
- **WHEN** Codex has reviewed the current head
- **THEN** the Claude fallback does not run

#### Scenario: Stale Codex review
- **WHEN** the only Codex review is for an older head
- **THEN** it is not accepted as evidence

#### Scenario: Codex review absent
- **WHEN** the wait ends without a review of the head by either trusted reviewer — none, or an error or limit message instead of one
- **THEN** the Claude Code action runs with the trusted contract and leaves inline `P0`–`P3` comments or a comment naming the reviewed head; the job then reads whether a review of the head under the workflow token exists — a silent fallback fails the check

#### Scenario: Re-run on a fallback head
- **WHEN** the head's run is re-run after its first attempt fell back to Claude and the fallback published its review of the head
- **THEN** the wait returns on that review, the Claude Code action does not run again, and the attempt concludes on the enforcement of the threads as they are

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
