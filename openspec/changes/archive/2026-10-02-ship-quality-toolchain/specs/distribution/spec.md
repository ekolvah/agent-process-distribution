## MODIFIED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, one marker-owned Dependabot entry, the
marker-owned block of `.pre-commit-config.yaml` — the whole file when the run creates it —, the
seeded `.github/agent-process-quality.json`, the skill
check `.claude/agent-process-check.py`, in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`, and, outside the working tree, the
pre-push hook of this clone that `pre-commit install --hook-type pre-push` writes. Every other
consumer file, key, and hook entry SHALL keep its content, and no publisher file is copied into
the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those eight files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical

### Requirement: Init asks for no quality command
`init` SHALL take no test or setup command. The quality commands of a repository SHALL live in
its own declaration `.github/agent-process-quality.json`, a JSON object with a non-blank string
`test` and optional string `setup` and `checks`, each on one line. When the declaration is
absent and the run creates `.pre-commit-config.yaml`, the run SHALL classify a `quality`
transition, printed before the `pre-commit` transition, whose write seeds the declaration with a
`setup` that installs `pre-commit` and `pytest` at this repository's pins and then each of
`requirements.txt` and `requirements-dev.txt` that exists, failing when an install fails, and the `test`
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

#### Scenario: Install without tests
- **WHEN** a dry-run or confirmed run meets a repository with `.pre-commit-config.yaml` and without `.github/agent-process-quality.json`
- **THEN** it prints no `quality` transition, its output carries one `quality: ` line naming the declaration before any `manual` row and no `manual quality-command` row, and a confirmed run writes no declaration

#### Scenario: Declared quality command
- **WHEN** a dry-run or confirmed run meets a valid declaration of a `test`
- **THEN** its output carries `unchanged quality` and no `quality: ` line, and the declaration keeps its bytes

#### Scenario: Upgrade over a passed test command
- **WHEN** a run meets a managed caller that passes a `test` input and no declaration of a `test`
- **THEN** it prints `conflict` naming the passed command and the declaration file, exits non-zero, and no consumer file has changed

## ADDED Requirements

### Requirement: Init seeds the baseline toolchain
A `.pre-commit-config.yaml` that a run creates SHALL set `minimum_pre_commit_version: "4.4.0"`
and SHALL declare, outside the agent-process block, these hooks. At the `pre-commit` and
`manual` stages: `ruff-check` of `astral-sh/ruff-pre-commit` with the rules `C901`, `PLR0911`,
`PLR0912`, `PLR0913` and `PLR0915` added to its selection, `ruff-format` of the same repository,
`mypy` of `pre-commit/mirrors-mypy` with `args: []`, so an import it cannot resolve fails the hook, `pylint` of `pylint-dev/pylint` with only `too-many-lines`
enabled at 1000 lines, and `detect-secrets` of `Yelp/detect-secrets`. At the `manual` stage
only: `pip-audit` of `pypa/pip-audit`, once for `requirements.txt` and once for
`requirements-dev.txt`, each running only while its file is tracked, and a local hook `pytest`
that runs `python -m pytest` of the `python` on `PATH` once, only while a file named
`test_*.py` or `*_test.py` is tracked. Each hook's `rev` SHALL equal this repository's pin of
that tool: ruff the `rev` of this repository's `.pre-commit-config.yaml`, every other tool its
`.agent-process/requirements-dev.txt` line. An existing `.pre-commit-config.yaml` SHALL keep
every byte outside the block.

#### Scenario: Created config
- **WHEN** a confirmed run creates `.pre-commit-config.yaml`
- **THEN** the file declares the agent-process block and those hooks at those stages, and each `rev` equals this repository's pin of its tool

#### Scenario: Tests run once they exist
- **WHEN** `pre-commit run --hook-stage manual --all-files` runs the created config's `pytest` hook in a repository with no tracked test file, and again after a failing `tests/test_a.py` is tracked
- **THEN** the first run reports the hook skipped and exits 0, and the second runs the test and exits non-zero

#### Scenario: Existing config keeps its hooks
- **WHEN** a confirmed run meets a `.pre-commit-config.yaml` with the agent-process block and hooks of the repository's own
- **THEN** every byte outside the block is unchanged and no baseline hook is added
