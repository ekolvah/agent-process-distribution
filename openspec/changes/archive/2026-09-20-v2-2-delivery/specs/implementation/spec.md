## ADDED Requirements

### Requirement: Quality commands belong to the consumer
The consumer SHALL declare its `setup` and `test` shell commands in the thin workflow
caller. The reusable quality workflow SHALL run them on the PR head, fail visibly when
either command fails, and run strict OpenSpec validation when the repository has an
OpenSpec root. The core SHALL NOT infer a language, package manager, linter, or test
runner.

#### Scenario: Consumer test fails
- **WHEN** the caller's `test` command exits non-zero on a PR head
- **THEN** the quality job for that head fails with the command output

## MODIFIED Requirements

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` from the `agent-process` skill before writing code; the pointer in the
`tasks` rule of `config.yaml` SHALL load that procedure. Documentation-only, rename and
one-line non-behavioural changes are exempt (`principles.md` §I). `check_red` SHALL run
`python -m pytest` of its own interpreter under its own configuration — fail-fast
cancelled, cache-driven selection and stepping disabled, and a JUnit XML report path of
its own choosing — with the node ids appended, and SHALL take the verdict per test from
that complete report without a caller-declared runner or report path.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit contains a test that `check_red` reports as failing

#### Scenario: Runner given
- **WHEN** `check_red` is called with node ids
- **THEN** it runs `python -m pytest` from its own interpreter and judges RED from the report that run writes

#### Scenario: Configuration that cuts the run
- **WHEN** pytest configuration would stop or replay the selected run early
- **THEN** `check_red` either runs every node id or exits 2 with the runner output, never RED from a partial report

### Requirement: The implementing run ends only after checks and reviews
The implementing run SHALL call `wait_for_pr` from the shared skill until every workflow
check on one settled PR head has concluded, then print unresolved review threads for the
agent to address or answer. The direct Claude review job is one of those checks. Codex
automatic review is advisory and SHALL NOT be converted into a custom pending signal or
required check; the person remains the final review and merge gate. The command SHALL
distinguish clean, unresolved, GitHub read failure, and timeout outcomes by exit code.

#### Scenario: Pending review
- **WHEN** the caller's Claude review job or another PR check is pending
- **THEN** `wait_for_pr` blocks and the implementing run cannot report completion

#### Scenario: Empty rollup after a push
- **WHEN** `wait_for_pr` runs before any check has attached to the new head
- **THEN** it reads again and reads threads only after the checks on a settled head have concluded

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
- **WHEN** a push addresses a `P0` or `P1` thread
- **THEN** the fixer may resolve that exact older-head thread from its own session and then waits for the caller checks again

#### Scenario: Review fix changes a spec
- **WHEN** a review fix changes what a spec requires
- **THEN** it uses and archives a change of its own instead of editing the main spec directly

#### Scenario: Design decision changed at review
- **WHEN** a review fix changes an archived design decision
- **THEN** the archived design and scenario-to-test map are amended in the same push

#### Scenario: Finding closed by its class
- **WHEN** a review finding concerns what a script does
- **THEN** the fix covers the violated invariant and its input class rather than only the reviewer's example

## REMOVED Requirements

### Requirement: ci_check is the one command every gate runs
**Reason**: consumers no longer receive the Python control plane or its pre-push hook; the
thin caller supplies the target repository's own setup and test commands.
**Migration**: put the repository's complete quality command in the caller's `test` input;
the publisher may continue to call its own `ci_check.py` through that input until v1 code
is deleted.

### Requirement: Shift-left feedback in Claude
**Reason**: the plugin ships no hooks; a copied hook stack would reintroduce the process
payload and language assumptions that v2 removes.
**Migration**: repository-local Claude settings MAY keep project-specific feedback, while
portable correctness runs through the caller's quality job.

### Requirement: Stop hook names the next command
**Reason**: the plugin ships no Stop hook; the OpenSpec apply procedure ends in the
explicit `wait_for_pr` step and the person remains the terminal gate.
**Migration**: follow the shared skill's delivery tasks and their exit codes.

### Requirement: A broken hook is visible
**Reason**: no hook is part of the distributed process after this change.
**Migration**: failures of required commands remain visible in `check_red`, quality, and
`wait_for_pr`.
