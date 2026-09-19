## MODIFIED Requirements

### Requirement: RED first for behavioural changes
The implementer SHALL write the failing test named in `tasks.md` and prove it red with
`check_red` before writing code; this is a `config.yaml` rule on `tasks`.
Documentation-only, rename and one-line non-behavioural changes are exempt (`principles.md`
§I). `check_red` SHALL run `python -m pytest` of its own interpreter under its own
configuration — fail-fast cancelled, the cache-driven selection and stepping disabled, a
JUnit XML report path of its own choosing — with the node ids appended, and SHALL take the
verdict per test from that report, whole; it SHALL require no runner declaration and no
report path of the project.

#### Scenario: Behavioural change
- **WHEN** the implementer starts a behavioural task
- **THEN** the first commit contains a test that `check_red` reports as failing

#### Scenario: Runner given
- **WHEN** `check_red` is called with node ids
- **THEN** the runner is a given — `python -m pytest` of the interpreter that runs the script, no runner argument — and it runs with the report path and the node ids appended and judges RED from the report the run wrote, without any declared report path

#### Scenario: Configuration that cuts the run
- **WHEN** the project's pytest configuration carries a flag that stops the run early or replays a previous run (`-x`, `--maxfail`, `--stepwise`, `--lf`, `--ff`)
- **THEN** `check_red` either runs every node id regardless or exits 2 with the runner's output, never RED from a partial report
