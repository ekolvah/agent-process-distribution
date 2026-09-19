## MODIFIED Requirements

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` before writing code; this is a `config.yaml` rule on `tasks`.
Documentation-only, rename and one-line non-behavioural changes are exempt (`principles.md`
§I). `check_red` SHALL run the test runner itself — the command given as its `--test`
input, `python -m pytest` when none is given — with a JUnit XML report path of its own
choosing and the node ids appended, and SHALL take the verdict per test from that report;
it SHALL require no runner declaration and no report path of the project.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit contains a test that `check_red` reports as failing

#### Scenario: Runner given
- **WHEN** `check_red` is called with `--test "<runner command>"` and node ids
- **THEN** it runs that command with the report path and the node ids appended and judges RED from the report the run wrote, without any declared report path
