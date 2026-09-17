## MODIFIED Requirements

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
