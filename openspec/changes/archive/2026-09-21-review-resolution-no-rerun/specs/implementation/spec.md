## MODIFIED Requirements

### Requirement: Delivery steps are tasks of every change
The `tasks` section of the shared `agent-process` skill, named by the `tasks` rule in
`config.yaml`, SHALL make every `tasks.md` begin with `start_change <change>` and end with
the consumer's quality command, `archive_change <change>`, PR creation, and the bounded
`wait_for_pr` thread loop. The propose run SHALL register the existing tracking issue in
`Planned` and write its number into Group 0 before implementation. The delivery SHALL NOT
post an `@codex review` request because the person enables automatic Codex reviews during
installation. After three rounds, remaining advisory findings SHALL be answered and left
to the person. The tasks after archive SHALL leave no tick in the repository, and an
interrupted run SHALL resume from the PR. Scripts SHALL be invoked from the loaded skill's
`scripts/` directory.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` starts through `start_change` on the registered issue, archives before PR creation, and contains no manual Codex review request

#### Scenario: Propose run stopped before its tail
- **WHEN** `start_change` runs before the issue token and `Planned` state are present
- **THEN** it exits 2 before creating a branch and names the unfinished propose run

#### Scenario: Verdict is rework
- **WHEN** `start_change` runs while the architect-review verdict is not `approve`
- **THEN** it exits 2 before creating a branch and names the rework

#### Scenario: Blocking thread addressed
- **WHEN** a pushed correction addresses a `P0` or `P1` thread and the current-head workflow has settled
- **THEN** the fixer may resolve that exact older-head thread from its own session and reply without re-running the combined workflow on the unchanged head

#### Scenario: Review fix changes a spec
- **WHEN** a review fix changes what a spec requires
- **THEN** it uses and archives a change of its own instead of editing the main spec directly

#### Scenario: Design decision changed at review
- **WHEN** a review fix changes an archived design decision
- **THEN** the archived design and scenario-to-test map are amended in the same push

#### Scenario: Finding closed by its class
- **WHEN** a review finding concerns what a script does
- **THEN** the fix covers the violated invariant and its input class rather than only the reviewer's example
