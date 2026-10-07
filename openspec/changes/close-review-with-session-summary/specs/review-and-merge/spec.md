## MODIFIED Requirements

### Requirement: Claude reviews every head
The review job SHALL read once whether a closing comment of the workflow token's login names
the current head, and when none does SHALL run the Claude Code action with the review
contract read from the trusted checkout of the process at the ref the caller pinned. The
action publishes findings as inline comments labelled `P0`–`P3` and has no tool to post a PR
comment. When the action concludes `success` and its session ended with a non-empty final
message, the job SHALL post the closing comment naming the head, carrying that final message
verbatim and every permission denial of the session — that comment alone is its review;
inline comments without it are review nodes an interrupted action leaves behind — and SHALL
read, within a bounded time, whether it exists; otherwise the job SHALL fail the check
without posting it. A permission denial SHALL NOT fail the check. The job leaves no review
state, no evidence and no classification, and nobody requests the review. On a
release PR the job SHALL neither read nor run the Claude Code action, and SHALL conclude on
the enforcement of the threads.

#### Scenario: New head
- **WHEN** the job runs on a head that no closing comment names — including a head whose only closing comment names an older head
- **THEN** the Claude Code action runs with the trusted contract and leaves inline `P0`–`P3` comments, and the job posts and then verifies the comment naming the head and carrying the session's final message

#### Scenario: Silent action
- **WHEN** the action finishes without concluding `success`
- **THEN** the job posts no closing comment and the check fails

#### Scenario: Silent finish
- **WHEN** the action concludes `success` but the session's final message is empty or the session left no result
- **THEN** the job posts no closing comment and the check fails

#### Scenario: Denied tool
- **WHEN** the session ended with a final message after one or more of its tool calls were denied
- **THEN** the closing comment lists each denied tool with its command on a line of its own, even a multi-line command, and the check does not fail on them

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
- **THEN** it runs the same path — the read, the action on absence, the closing comment, the verification, the enforcement — so its conclusion derives from a review of the head

#### Scenario: Release PR review
- **WHEN** the job runs on a release PR
- **THEN** it reads no review, the Claude Code action does not run, and the check passes unless an unresolved `P0`/`P1` thread exists
