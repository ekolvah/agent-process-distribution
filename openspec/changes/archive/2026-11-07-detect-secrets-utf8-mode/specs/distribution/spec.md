## MODIFIED Requirements

### Requirement: Init seeds the baseline toolchain
A `.pre-commit-config.yaml` that a run creates SHALL set `minimum_pre_commit_version: "4.4.0"`
and SHALL declare, outside the agent-process block, these hooks. At the `pre-commit` and
`manual` stages: `ruff-check` of `astral-sh/ruff-pre-commit` with the rules `C901`, `PLR0911`,
`PLR0912`, `PLR0913` and `PLR0915` added to its selection, `ruff-format` of the same repository,
`mypy` of `pre-commit/mirrors-mypy` with `args: []`, so an import it cannot resolve fails the
hook, `pylint` of `pylint-dev/pylint` with only `too-many-lines` enabled at 1000 lines, and a
local hook `detect-secrets` that runs detect-secrets in Python UTF-8 mode. At the `manual` stage
only: `pip-audit` of `pypa/pip-audit`, once for `requirements.txt` and once for
`requirements-dev.txt`, each running only while its file is tracked, and a local hook `pytest`
that runs `python -m pytest` of the `python` on `PATH` once, only while a file named
`test_*.py` or `*_test.py` is tracked. Each hook's `rev`, and the `detect-secrets` hook's pinned
dependency, SHALL equal this repository's pin of that tool: ruff the `rev` of this repository's
`.pre-commit-config.yaml`, every other tool its `.agent-process/requirements-dev.txt` line. An
existing `.pre-commit-config.yaml` SHALL keep every byte outside the block.

#### Scenario: Created config
- **WHEN** a confirmed run creates `.pre-commit-config.yaml`
- **THEN** the file declares the agent-process block and those hooks at those stages, and each pin equals this repository's pin of its tool

#### Scenario: Tests run once they exist
- **WHEN** `pre-commit run --hook-stage manual --all-files` runs the created config's `pytest` hook in a repository with no tracked test file, and again after a failing `tests/test_a.py` is tracked
- **THEN** the first run reports the hook skipped and exits 0, and the second runs the test and exits non-zero

#### Scenario: Secret in a file the locale cannot decode
- **WHEN** `pre-commit run --hook-stage manual --all-files` runs the created config's `detect-secrets` entry with `PYTHONUTF8=0`, `PYTHONCOERCECLOCALE=0` and `LC_ALL=C` on a tracked UTF-8 file whose only line is `ключ сервиса: aws_secret_access_key = "<an AWS example key>"`
- **THEN** the run exits non-zero and reports a secret at that file's line 1

#### Scenario: Existing config keeps its hooks
- **WHEN** a confirmed run meets a `.pre-commit-config.yaml` with the agent-process block and hooks of the repository's own
- **THEN** every byte outside the block is unchanged and no baseline hook is added
