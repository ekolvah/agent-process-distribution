## MODIFIED Requirements

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

## REMOVED Requirements

### Requirement: Local safety on both carriers
**Reason**: Codex left the process; "Local safety in Claude Code" replaces it.
**Migration**: none; the Claude Code deny-list is unchanged.

### Requirement: No automation resolves a review thread
**Reason**: threads of the Codex app are no longer trusted; "Only the fixer resolves a
review-job thread" replaces it.
**Migration**: none.

### Requirement: Codex reviews on the author's request, Claude is the fallback
**Reason**: Codex left the process (decided 2026-09-27); Claude Code reviews every head with
no fallback.
**Migration**: "Claude reviews every head" replaces it; the author requests no review, and a
repository with the Codex GitHub app uninstalls it or turns its reviews off.

## ADDED Requirements

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
