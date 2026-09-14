## ADDED Requirements

### Requirement: PR review is advisory
The Codex GitHub app SHALL review every PR by its own configuration and a short
`claude-code-action` workflow SHALL review the diff. Neither verdict SHALL be classified by
a script or turned into a required check.

#### Scenario: Blocking finding
- **WHEN** a reviewer reports a blocking finding
- **THEN** the merge button state does not change; the thread stays unresolved

### Requirement: The reviewer reads the diff and the scenarios
The reviewer SHALL read the diff together with the change's spec delta and report a test
that does not actually check the scenario it is mapped to. The PR body SHALL list tracked
deferrals as issue links so a reviewer does not re-report them.

#### Scenario: Deferred finding
- **WHEN** the PR body links an issue for a known gap
- **THEN** the reviewer does not report that gap again

### Requirement: A later fix is a new implement run
A fix after the implementing run has ended SHALL be the person running `/implement <change>`
again; that run reads the open threads.

#### Scenario: Thread after completion
- **WHEN** a thread is opened after the run ended
- **THEN** the next `/implement <change>` run starts from the open threads

### Requirement: The person merges
No agent SHALL have merge authority.

#### Scenario: Agent attempts merge
- **WHEN** an agent runs `gh pr merge`
- **THEN** the deny-list or the ruleset rejects it

### Requirement: Reviewer instructions name the simplicity triggers
Reviewer instructions SHALL name reinvented functionality and unnecessary complexity as
findings to raise.

#### Scenario: Reinvented helper
- **WHEN** a PR adds a helper that `gh` already provides
- **THEN** the reviewer raises it

### Requirement: No review state machine
The core SHALL NOT classify outcomes, publish evidence, preflight review credentials, fail
over between reviewers, or drift-check branch protection.

#### Scenario: Reviewer unavailable
- **WHEN** the Codex app does not review a PR
- **THEN** the PR waits for the other reviewer or the person; nothing fails over
