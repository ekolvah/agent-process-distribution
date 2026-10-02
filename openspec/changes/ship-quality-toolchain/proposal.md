## Why

A repository that adopts the process gets the quality gates but none of the quality tools
(#328). A fresh install declares no per-file hook (`skills/agent-process/templates/pre-commit-config.yaml`
holds only the `pre-push` hook `quality`) and no quality command (`init` never writes
`.github/agent-process-quality.json`, issue 249), so edit-time lint, the pre-push hook and
`agent-process / quality` run no formatter, linter, type checker, complexity or size limit, secret
scan, dependency audit or test until someone adds each by hand. This repository runs all of them
through its publisher-only `ci_check`, which no consumer receives.

Scope decision of the person: the consumer's stack is the plugin's own — Python, `pip`
lockfiles, `pytest`, `pre-commit`. Other stacks are not considered here.

Observed before planning:

- Consumer of record `kinozal_scraper` (GitHub languages: Python only) keeps root
  `requirements.txt`/`requirements-dev.txt` compiled by pip-tools, a `pyproject.toml`, its own
  `scripts/ci_check.py` declared as `test`, and a `.pre-commit-config.yaml` whose only content is
  the agent-process block (`rev: v3.2.8`, hook `quality`).
- `init` writes the whole template only when `.pre-commit-config.yaml` is absent or blank; an
  existing file gets only the marker block replaced, and a file without the block is a
  `conflict` (`_block_text`, `skills/agent-process/scripts/init.py`). Content outside the block
  is therefore written once and owned by the repository after that.
- The standard hook repositories, read with `gh api repos/<repo>/contents/.pre-commit-hooks.yaml`:
  `pre-commit/mirrors-mypy` hook `mypy` runs in an isolated environment with
  `args: ["--ignore-missing-imports", "--scripts-are-modules"]`; `pypa/pip-audit` hook
  `pip-audit` has `pass_filenames: false`; `Yelp/detect-secrets` hook `detect-secrets`,
  `pylint-dev/pylint` hook `pylint`, `astral-sh/ruff-pre-commit` hooks `ruff-check` and
  `ruff-format`. Tags matching this repository's pins exist: mirrors-mypy `v1.20.2`, pylint
  `v4.0.9`, pip-audit `v2.10.0`, detect-secrets `v1.5.0`; ruff is pinned by this repository's
  hook `rev: v0.15.12`.
- pre-commit 4.6.0 in a scratch repository with local hooks: `pre-commit run --hook-stage manual
  --all-files` ran a hook staged `[pre-commit, manual]` on every file, printed
  `tests....(no files to check)Skipped` and exited 0 for a `manual` hook whose `files` matched
  nothing, ran that hook once a `tests/test_a.py` existed, and never ran the `pre-push`-only hook;
  `--hook-stage pre-commit --files tests/test_a.py` ran only the `pre-commit`-staged hook.
- The baseline of design D2, live with pre-commit 4.6.0 on Windows, in a scratch repository
  whose `pyproject.toml` selects ruff's `B` rules, with a function of 11 branches and 7
  parameters, a 1005-line module, a `requirements.txt` pinning `requests==2.31.0` and a passing
  `tests/test_a.py`: the cold `--hook-stage pre-commit --files a.py` run installed four
  environments and finished in 73 s; `--hook-stage manual --all-files` reported `B006`, `C901`
  and `PLR0913` (the repository's own selection kept), pylint `C0302 Too many lines in module
  (1005/1000)`, pip-audit's vulnerabilities for `requirements.txt`, `pip-audit
  requirements-dev.txt...(no files to check)Skipped`, and `pytest...Passed`. Written unquoted,
  `args: [--extend-select=C901,PLR0911,...]` is split by YAML at each comma, and ruff printed
  `Failed to lint PLR0911` for each rule taken as a path.
- The same repository with the `mypy` hook given `args: []` and a `b.py` calling
  `requests.get(url).json_data()`: mypy failed with `Library stubs not installed for "requests"
  [import-untyped]`; with `additional_dependencies: [types-requests]` it failed with
  `"Response" has no attribute "json_data"`. mypy's documentation: "We recommend avoiding
  `--ignore-missing-imports` if possible"; the Scientific Python development guide: "You should
  always specify args, as the hook's default hides issues"; `psf/black` runs mirrors-mypy with
  `args: []` and an `additional_dependencies` list.
- The reusable `quality` workflow runs `setup` only in CI, on `ubuntu-latest`, as
  `run: eval "$SETUP"` (`.github/workflows/quality.yml`); the pre-push hook runs only `test`. A
  `for f in requirements.txt requirements-dev.txt; do if [ -f "$f" ]; then ... || exit 1; fi;
  done` loop under `bash -e -c 'eval ...'` exited 0 with neither file, and 1 when an install failed.
- pre-commit's CHANGELOG, 4.4.0: "Add `language: unsupported` / `language: unsupported_script`
  as aliases for `language: system` / `language: script`".

## What Changes

- The `.pre-commit-config.yaml` that `init` creates carries, outside the agent-process block, a
  baseline toolchain the repository then owns: `ruff-check` (with complexity limits),
  `ruff-format`, `mypy` (with `args: []`, so an unresolved import is an error rather than `Any`), `pylint` (module size) and `detect-secrets` at the `pre-commit` and
  `manual` stages, and at the `manual` stage only `pip-audit` per lockfile and `pytest` once test
  files exist. Hook revisions equal this repository's pins.
- `init` seeds `.github/agent-process-quality.json` — `setup` installs the pinned `pre-commit` and
  `pytest` and each tracked `requirements.txt` / `requirements-dev.txt`, `test` runs `pre-commit run --hook-stage manual --all-files --show-diff-on-failure` — when the
  declaration is absent and the run also creates `.pre-commit-config.yaml`. It never rewrites an
  existing declaration. This revises the issue-249 decision that the installer writes no
  declaration; ADR 0035 records it.
- An existing `.pre-commit-config.yaml` and an existing declaration keep their content; the
  `quality:` status line stays for a repository left without a declaration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the installed footprint adds the seeded files; `init` seeds the declaration;
  a new requirement for the baseline toolchain the created `.pre-commit-config.yaml` carries.

## Impact

- Added: `.agent-process/docs/adr/0035-init-seeds-a-baseline-quality-toolchain.md`,
  `skills/agent-process/templates/agent-process-quality.json`.
- Edited: `skills/agent-process/templates/pre-commit-config.yaml` (baseline outside the block),
  `skills/agent-process/scripts/init.py` (the `quality` step, the status-line condition,
  docstring), `skills/agent-process/scripts/quality.py` (docstring: the installer seeds the
  declaration with a created config), `skills/agent-process/SKILL.md` (Install step 1, the
  edit-time lint paragraph),
  `tests/publisher/test_init.py`, `tests/publisher/test_init_config.py`,
  `tests/publisher/init_harness.py` (`CONSUMER_FILES`, `LABELS`), `tests/publisher/test_init_remote.py` if
  its fixture needs the new file.
- Removed: none.
- Unchanged by decision: `ci_check` and this repository's own `.pre-commit-config.yaml`,
  `check_red` (its guard and message still hold for a repository without a seeded declaration),
  `quality.py` behaviour, the reusable `quality` workflow, existing consumers' files.
