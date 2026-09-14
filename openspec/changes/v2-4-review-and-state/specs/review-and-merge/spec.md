## ADDED Requirements

### Requirement: PR review is advisory
The Codex GitHub app SHALL review every PR by its own configuration and a short
`claude-code-action` workflow SHALL review the diff. Neither verdict SHALL be classified by
a script or turned into a required check; an unresolved thread blocks merging through the
ruleset's conversation resolution, not through the verdict.

#### Scenario: Blocking finding
- **WHEN** a reviewer reports a blocking finding as a thread
- **THEN** no check turns red and the PR is unmergeable until the thread is resolved

### Requirement: The reviewer reads the diff and the scenarios
The reviewer SHALL read the diff together with the change's spec delta and report a test
that does not actually check the scenario it is mapped to. The PR body SHALL list tracked
deferrals as issue links so a reviewer does not re-report them.

#### Scenario: Deferred finding
- **WHEN** the PR body links an issue for a known gap
- **THEN** the reviewer does not report that gap again

### Requirement: A later fix is a new implement run
A fix after the implementing run has ended SHALL be a new agent run that the person starts
on the open PR; it begins with `wait_for_pr`, which prints the open threads. The change is
archived by then, so the fix commits code, tests and, when a requirement changes, the
archived delta together with `openspec/specs/` directly; a rework that changes what the PR
delivers is a new change. No active change SHALL be required for a fix.

#### Scenario: Thread after completion
- **WHEN** a thread is opened after the run ended
- **THEN** the next run on the PR starts from the threads `wait_for_pr` prints, without an active change

### Requirement: The person merges
No agent SHALL merge. In Claude Code the deny-list SHALL reject `gh pr merge`; in Codex,
which shares the person's `gh` session and has no hooks, the prohibition SHALL be a rule in
`AGENTS.md` — a ruleset cannot tell the agent from the person, and an observed violation is
what would justify a Codex-side mechanism.

#### Scenario: Agent attempts merge
- **WHEN** an agent runs `gh pr merge`
- **THEN** in Claude Code the deny-list rejects it; in Codex the run has broken the `AGENTS.md` rule and the person sees a merge they did not make

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
