## Context

See proposal.md — Why for the observations. Three triggers already read per-repository
declarations: the plugin's edit-time lint runs the `pre-commit`-stage hooks of
`.pre-commit-config.yaml` (ADR 0034), the pre-push hook `quality` and the reusable `quality`
workflow run the `test` of `.github/agent-process-quality.json` (issue 249). Only the content of
those two files is missing in a fresh consumer. Scope (the person's decision): the consumer's
stack is the plugin's — Python, `pip` lockfiles, `pytest`, `pre-commit`.

## Goals / Non-Goals

**Goals:** a fresh install runs a formatter, linter with complexity limits, type checker,
module-size limit and secret scan after each edit, at push and in CI, and the dependency audit
and the tests at push and in CI, with no per-repository assembly.

**Non-Goals:** other stacks; changing an existing consumer's files (kinozal_scraper keeps its
own `ci_check`); enforcing the baseline as a minimum the repository cannot narrow; moving this
repository's `ci_check` onto the baseline; keeping consumers' hook revisions current (a
repository runs `pre-commit autoupdate`; a Dependabot `pre-commit` entry is a later change once
stale revisions are observed).

## Decisions

- **D1 — The baseline is template content outside the marker block.** `init` writes the whole
  template only when it creates the file, and replaces only the block afterwards
  (`_block_text`), so content outside the block is seeded once and owned by the repository,
  which may extend or narrow it; no new installer mechanism. Alternatives: hooks inside the
  block — every upgrade would rewrite them, and a repository could not narrow them; merging into
  an existing file — rewriting YAML the installer does not own, which `Init fails closed on
  inputs it does not own` forbids.

- **D2 — The hooks are the standard hook repositories, staged by cost.** Per-file and fast —
  `ruff-check`, `ruff-format`, `mypy`, `pylint`, `detect-secrets` — run at `pre-commit` (edit
  time) and `manual` (gate). Whole-repository or networked — `pip-audit`, `pytest` — run at
  `manual` only. Stage semantics observed with pre-commit 4.6.0 (proposal, Why).
  - Complexity: `ruff-check` `args: ["--extend-select=C901,PLR0911,PLR0912,PLR0913,PLR0915"]`,
    the rules ADR 0028 chose, with ruff's default thresholds; `--extend-select` adds to a
    repository's own `[tool.ruff]` selection instead of replacing it (observed, proposal Why).
    The argument is quoted: unquoted, YAML splits it at each comma (observed).
  - Module size: `pylint` `args: [--disable=all, --enable=too-many-lines, --max-module-lines=1000]`,
    as this repository's `[tool.pylint]` (ADR 0028: ruff has no module-length rule). It
    imports nothing, so pylint's isolated environment suffices.
  - Type checker: `mirrors-mypy` with `args: []`, the documented practice (proposal Why): the
    hook's default `--ignore-missing-imports` turns every library it cannot see into `Any`
    silently (§IV). With `args: []` an import of a library the isolated environment lacks fails
    with `Library stubs not installed for "<lib>"` or `Cannot find implementation or library
    stub`; the repository adds the stub or the typed library to `additional_dependencies` once,
    and calls into it are checked from then on (observed). The list duplicates part of the
    requirements: a library missing from it fails visibly, an extra one is harmless, a version
    skew of a stub is the remaining drift; no standard tool syncs them. Alternatives: the default
    args — the silent `Any`; mypy in the project environment (`language: unsupported`) — fails
    every edit and push until the repository installs mypy, the per-repository step this change
    removes; and the same at the `manual` stage only — the first push of a fresh repository fails
    on `No module named mypy`.
  - Secrets: `detect-secrets` without a baseline, as `ci_check` (a baseline is a "make it green"
    button).
  - Audit: `pip-audit` twice, `args: [-r, requirements.txt]` with `files: ^requirements\.txt$`
    and the same for `requirements-dev.txt` (pip-tools lockfiles, the layout of
    kinozal_scraper); with `pass_filenames: false` the hook runs once, only while the file is
    tracked, else pre-commit prints it `Skipped`.
  - Tests: pytest publishes no pre-commit hook of its own, hence a local hook `entry: python -m pytest`, `language: unsupported`,
    `pass_filenames: false`, `files: (^|/)(test_[^/]*|[^/]*_test)\.py$` — pytest's default
    `python_files`; pytest's own configuration chooses what runs. `unsupported` (pre-commit
    ≥ 4.4.0, CHANGELOG) runs the `python` on `PATH`, which sees the project's dependencies;
    `minimum_pre_commit_version: "4.4.0"` makes an older pre-commit say so instead of failing
    on an unknown language. Alternative: `language: system` — the alias pre-commit says it
    will deprecate.

- **D3 — One pin per tool.** Each rendered `rev` equals this repository's pin (ruff: its own
  hook `rev`; mypy, pylint, detect-secrets, pip-audit, pre-commit, pytest:
  `.agent-process/requirements-dev.txt`), asserted by a publisher test, so a consumer gets only
  versions the publisher runs, and a bump is one PR that moves both. The `rev` of mirrors-mypy
  is the mypy version (`v1.20.2`).

- **D4 — `init` seeds the declaration with the config (revises issue 249).** 249's premise was
  that a repository without tests has no command to declare; with the baseline it has one. The
  `quality` step writes `{"setup": "python -m pip install pre-commit==<pin> pytest==<pin> && for
  f in requirements.txt requirements-dev.txt; do if [ -f \"$f\" ]; then python -m pip install -r
  \"$f\" || exit 1; fi; done", "test": "pre-commit run --hook-stage manual --all-files
  --show-diff-on-failure"}` (pins of pre-commit and pytest from
  `.agent-process/requirements-dev.txt`, D3) only when the declaration is absent and the
  `.pre-commit-config.yaml` is absent or blank — the run that creates the baseline. `setup` runs
  in CI only, in bash (proposal Why): it installs the tools the `local` `pytest` hook needs and
  the project's packages from whichever lockfile exists; a lockfile's own `pytest` pin, installed
  after, wins. It is ordered before `pre-commit`, so a retry after an interrupted run
  still sees the config absent and converges. Output: the step prints `planned`/`written` when
  it seeds and `unchanged` whenever the declaration exists, as every file step does, so the
  label set of a fresh run and of a rerun stays the same (`test_lifecycle` asserts it); with no
  declaration beside an existing config it prints no transition, and the `quality:` status line
  speaks instead. The `test` runs at the `manual` stage, which
  excludes the `pre-push` hook `quality` that runs this `test` — no recursion; this repository
  already runs a stage-filtered `pre-commit run` as its declared `test` under that hook on every
  push (`ci_check.check_lint`). Alternatives:
  seed whenever the declaration is absent — a repository with an existing config would get a
  `test` that runs none of the baseline and turns CI silently green (§IV); the status line
  stays for it instead. The quality callee or `quality.py` running pre-commit when no
  declaration exists — a second, implicit source of the gate's command.

- **D5 — What the seeded declaration takes away, and its catchers.** The seeded `test` replaces
  a project-declared input with one the installer supplies:
  - Lost proof: `check_red` exits 2 until a `test` is declared, so the change with the first
    tests had to declare one that runs them. With the seed, the guard passes from install.
    Catcher: the baseline `pytest` hook runs in that `test` once a test file is tracked —
    `agent-process / quality` on the first-tests PR's head, and the pre-push hook on the same
    push.
  - Failure mode: tests need packages outside both lockfiles (a `pyproject.toml` extra, another
    file name) — that PR's `agent-process / quality` fails with `No module named ...`, visible;
    the repository extends `setup`.
  - Failure mode: a repository that changes pytest's `python_files` keeps the hook's `files`
    regex — pre-commit prints `pytest...(no files to check)Skipped` in the gate's log; the
    repository owns the regex.
  - Failure mode: a repository with code of its own and no `.pre-commit-config.yaml` (ADR 0018's
    established-project adoption) gets the baseline too, so its installation PR's
    `agent-process / quality` runs it over pre-adoption code — `ruff-format` diffs, mypy errors
    per stub-less library — and fails, visibly, before `activate_protection`. Remedy: the
    repository owns that content (D1), so its own commit on that PR narrows the baseline, adds
    the `additional_dependencies` lines, or fixes the findings. Install step 1 says so before
    `--confirm`.
  - Failure mode: no `manual`-stage hook remains after a repository narrows the config — the
    `test` passes with nothing run; the narrowing is the repository's own commit in its PR.

- **D6 — Documentation.** SKILL.md Install step 1 says a run that creates the config seeds the
  baseline and its declaration, that a repository with existing code then makes the baseline
  pass on its installation PR (D5), otherwise the change that adds the first tests declares it; the edit-time
  lint paragraph replaces "the template declares none" and its advice to declare
  `pre-commit run --hook-stage pre-commit --all-files` as the `test`, which the seeded
  `--hook-stage manual` command supersedes. ADR 0035 records D1–D5 and supersedes
  the "installer writes no declaration" clause of issue 249 (`quality.py` docstring updated).

This adds no script: every check is a standard tool through pre-commit's own hook repositories.

## Risks / Trade-offs

- [The first edit-time run installs four hook environments from the network] → observed 73 s
  (proposal Why) against ADR 0034's 120 s timeout; ADR 0035 records the number. A slower first
  run is reported by the existing timeout, environments installed before it are kept, and the
  next edit continues.
- [detect-secrets on Windows reads files in the platform encoding and skips undecodable ones
  (`ci_check._secrets_cmd`)] → edit time on Windows may miss a secret in a non-ASCII file; the
  gate in CI runs on Linux with UTF-8.
- [Each new untyped or stub-less library fails mypy until it is listed] → one line of
  `additional_dependencies`, named by mypy's own message; recorded in ADR 0035.
- [CI installs the lockfiles on every run] → tens of seconds per run, the price of tests and
  audits against the real packages.
- [`pre-commit run --all-files` rewrites files a formatter changes] → as ADR 0034 for this
  repository: `--show-diff-on-failure` shows the diff and the run fails.
- [Consumers' revisions age] → Non-Goal; `pre-commit autoupdate` is the standard.

## Migration Plan

Only a run that creates `.pre-commit-config.yaml` — an empty repository or an established one
adopting the process (D5) — gets the baseline; existing consumers' files are untouched. Rollback: restore the template and
remove the `quality` step; repositories that already received the baseline keep it as their own.
