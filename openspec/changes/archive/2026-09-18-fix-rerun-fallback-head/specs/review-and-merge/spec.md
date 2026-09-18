## MODIFIED Requirements

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
