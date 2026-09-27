## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Local safety on both carriers
Push to the default branch, force push and `gh pr merge` SHALL be denied locally on both
carriers: a deny-list in Claude Code, a pre-tool hook in Codex. Merging is the person's, except
the release PR, which the platform's auto-merge merges once its required checks pass.

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
review state, no evidence and no classification. On a release PR the job SHALL neither wait
nor run the Claude Code action, and SHALL conclude on the enforcement of the threads.

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

#### Scenario: Release PR review
- **WHEN** the job runs on a release PR
- **THEN** it requests and waits for no review, the Claude Code action does not run, and the check passes unless an unresolved `P0`/`P1` thread exists

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
