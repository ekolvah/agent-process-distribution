## MODIFIED Requirements

### Requirement: Init asks for no quality command
`init` SHALL take no test or setup command. The quality commands of a repository SHALL live in
its own declaration `.github/agent-process-quality.json`, a JSON object with a non-blank string
`test` and optional string `setup` and `checks`, each on one line. When the declaration is
absent and the run creates `.pre-commit-config.yaml`, the run SHALL classify a `quality`
transition, printed before the `pre-commit` transition, whose write seeds the declaration with a
`setup` that installs `pre-commit` and `pytest` without a version together with each of
`requirements.txt` and `requirements-dev.txt` that exists, in one install that fails the
command when it fails, and the `test`
`pre-commit run --hook-stage manual --all-files --show-diff-on-failure`. `init` SHALL write the
declaration in no other case and SHALL never change an existing one; while it exists, the run
SHALL print the `quality` transition `unchanged`. While the declaration is
absent or declares no valid `test` and the run plans no `quality` transition, the output of a
dry-run and of a confirmed run SHALL carry, before the `manual` rows, one status line starting
`quality: ` that names the declaration and says CI runs no tests until the declaration exists,
and no `manual` row about it. An existing
managed caller that passes a `test` input while the declaration declares no `test` SHALL be
reported as `conflict` naming that input, and the run SHALL exit non-zero before any write.

#### Scenario: Fresh install seeds the declaration
- **WHEN** a dry-run and then a confirmed run meet a repository with neither `.github/agent-process-quality.json` nor `.pre-commit-config.yaml`
- **THEN** the dry-run prints `planned quality` before `planned pre-commit` and writes nothing, the confirmed run writes the declaration with that `setup` and `test`, and neither output carries a `quality: ` line

#### Scenario: Project requirements own the tool versions
- **WHEN** the seeded `setup` runs where `requirements-dev.txt` pins `pytest` at a version other than its latest release
- **THEN** the installed `pytest` and each version the requirements pin are the pinned versions

#### Scenario: Install without tests
- **WHEN** a dry-run or confirmed run meets a repository with `.pre-commit-config.yaml` and without `.github/agent-process-quality.json`
- **THEN** it prints no `quality` transition, its output carries one `quality: ` line naming the declaration before any `manual` row and no `manual quality-command` row, and a confirmed run writes no declaration

#### Scenario: Declared quality command
- **WHEN** a dry-run or confirmed run meets a valid declaration of a `test`
- **THEN** its output carries `unchanged quality` and no `quality: ` line, and the declaration keeps its bytes

#### Scenario: Upgrade over a passed test command
- **WHEN** a run meets a managed caller that passes a `test` input and no declaration of a `test`
- **THEN** it prints `conflict` naming the passed command and the declaration file, exits non-zero, and no consumer file has changed
