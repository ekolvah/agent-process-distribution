---
status: "accepted"
date: 2026-10-02
decision-makers: ekolvah
---

# Init seeds a baseline quality toolchain

## Context and Problem Statement

A fresh consumer got the triggers — the plugin's edit-time lint
([ADR 0034](0034-edit-time-lint-runs-the-projects-pre-commit-config.md)), the pre-push hook
`quality` and the reusable `quality` workflow — but nothing for them to run: its
`.pre-commit-config.yaml` held only the agent-process block, and issue 249 left
`.github/agent-process-quality.json` to the change that adds the first tests (#328). Each
consumer assembled its own linters, or ran none. Scope: the consumer's stack is the plugin's —
Python, `pip` lockfiles, `pytest`, `pre-commit`.

## Considered Options

* Seed the baseline as template content outside the marker block, and the declaration with it
* Hooks inside the marker block
* Merge the baseline into an existing config
* The `quality` callee runs pre-commit when no declaration exists

## Decision Outcome

Chosen: **a run that creates `.pre-commit-config.yaml` writes the baseline outside the marker
block and seeds the declaration that runs it**, in line with
[ADR 0027](0027-v2-standards-replace-the-bespoke-control-plane.md): every check is a standard
tool through its own hook repository; no script is added.

* D1 — Content outside the block is written once, when `init` creates the file, and owned by
  the repository afterwards, which may extend or narrow it; an existing config is untouched.
* D2 — Per-file hooks (`ruff-check` with C901 and PLR0911–PLR0915, `ruff-format`, `mypy` with
  `args: []`, `pylint` limited to `too-many-lines`, `detect-secrets`) run at `pre-commit` and
  `manual`; `pip-audit` per lockfile and a local `pytest` hook (`language: unsupported`, hence
  `minimum_pre_commit_version: "4.4.0"`) at `manual` only. mypy without
  `--ignore-missing-imports`: a library the hook environment lacks fails visibly until the
  repository lists its types in `additional_dependencies`, instead of becoming `Any`.
* D3 — Each `rev` and the seeded `pre-commit` and `pytest` pins equal this repository's pins,
  asserted by `tests/publisher/test_init_config.py` and `tests/publisher/test_init.py`.
* D4 — The `quality` step seeds `{"setup": <install pre-commit, pytest and each present
  requirements file>, "test": "pre-commit run --hook-stage manual --all-files
  --show-diff-on-failure"}` only when neither file exists; an existing declaration is
  `unchanged`; with an existing config and no declaration the `quality:` status line stays.
  This supersedes issue 249's "the installer writes no declaration".
* D5 — The seed takes away `check_red`'s proof that the first-tests change declared a `test`;
  the `pytest` hook runs once a test file is tracked, in that PR's gate. A repository that
  redefines pytest's `python_files` gets `pytest...Skipped` until it edits the hook's `files`.
  An established repository adopting the process runs the baseline over its existing code on
  the installation PR and fixes or narrows it there (SKILL.md Install step 1).

### Consequences

* Good, because a fresh install lints, type-checks, scans and tests after each edit, at push and
  in CI with no per-repository assembly.
* Good, because the edit-time run is a subset of the gate: one file declares both.
* Bad, because the first edit-time run installs four hook environments from the network
  (observed 73 s, inside ADR 0034's 120 s timeout).
* Bad, because each stub-less library fails mypy until it is listed, and that list partly
  duplicates the requirements.
* Bad, because consumers' revisions age; `pre-commit autoupdate` is theirs to run.

### Confirmation

`tests/publisher/test_init.py::test_quality_command_marker`,
`tests/publisher/test_init_config.py::test_created_config_carries_the_baseline`,
`::test_existing_config_keeps_its_hooks` and `::test_baseline_runs_tests_once_they_exist`.

## Native alternatives considered

| Script | Native feature tried or ruled out | Why it falls short |
| --- | --- | --- |
| none | The tools' own pre-commit hook repositories, staged by `stages` | Adopted: no script is added |
| none | mypy's hook default `--ignore-missing-imports` | Turns every unseen library into `Any` silently |

## Deletion condition

* Consumers of other stacks are supported → the Python baseline becomes one of several
  templates, chosen by the stack.
* pre-commit or the plugin ships a standard baseline a consumer enables without a template →
  the baseline and the seeded declaration are removed from the template.
