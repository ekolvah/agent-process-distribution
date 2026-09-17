## MODIFIED Requirements

### Requirement: Codex reviews on the author's request, Claude is the fallback
The PR author SHALL request the Codex review (`@codex review`, after the PR opens and after
every push; automatic reviews in the Codex app stay off). The review job SHALL wait a
bounded time for a Codex review of the current head — read as present or absent, never
parsed: a native review by the app on that head, or its clean comment naming that head;
an error or usage-limit message from the app is absence — and SHALL run the Claude Code
action with the review contract read from the trusted checkout of the process at the ref the
caller pinned only when the wait ended absent and the head is in the repository itself: the
action holds the repository's secret and runs what the PR worktree's `.claude/settings.json`
names, so it never meets a checkout the repository does not own. Each reviewer publishes findings as inline
comments labelled `P0`–`P3` and names the reviewed head when it finds nothing; the job leaves
no review state, no evidence and no classification.

#### Scenario: Valid Codex review
- **WHEN** Codex has reviewed the current head
- **THEN** the Claude fallback does not run

#### Scenario: Stale Codex review
- **WHEN** the only Codex review is for an older head
- **THEN** it is not accepted as evidence

#### Scenario: Codex review absent
- **WHEN** the wait ends without a Codex review of the head — none, or an error or limit message instead of one
- **THEN** the Claude Code action runs with the trusted contract and leaves inline `P0`–`P3` comments or a comment naming the reviewed head; the job then reads whether a review of the head under the workflow token exists — a silent fallback fails the check

#### Scenario: Reader failure
- **WHEN** the read of the PR's reviews fails instead of establishing presence or absence
- **THEN** the check fails without running the Claude action

#### Scenario: Head from a fork
- **WHEN** the PR head is in another repository and the wait ended absent, on any event
- **THEN** the Claude action does not run and the verification fails the check: the secret never meets the fork's checkout, and a fork PR is reviewed by Codex or by a person

#### Scenario: Event other than a push
- **WHEN** a caller runs the job for an event that is not `pull_request`
- **THEN** it runs the same path — the wait, the fallback on absence, the verification, the enforcement — so its conclusion derives from a review of the head; a run that only enforced would pass a head without any review

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
- **WHEN** a review is submitted on the PR — a reply on a thread is one
- **THEN** the caller runs the check again on the unchanged head; a resolve has no event of its own, so the fixer's reply after the resolve is what re-runs the check on the resolved state
