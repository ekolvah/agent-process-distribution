## Why

A consumer clone gets no local check before a push (#188). Install step 4 once told each clone
to set `core.hooksPath .agent-process/.githooks`, but the installer creates no such path, and
#185 removed the sentence. The publisher's own hook cannot be copied: it is a bash script that
runs this repository's `ci_check.py`, and the footprint forbids copying publisher files. The
first delivery push is covered by the Verify group; a corrective push after review findings can
reach CI unchecked, and `agent-process / quality` then blocks the merge only after an extra CI
round, push and review request.

The issue's plan (bake the `init --test` value into a `repo: local` hook) is overtaken: since
#249 `init` takes no command and never writes `.github/agent-process-quality.json`, which the
change that adds the first tests declares after installation. The hook has to read that
declaration when it runs.

**Observations (2026-09-29, Windows 11, Git for Windows bash 5.2.26, pre-commit 4.6.0, scratch
repository with a bare `origin`).**
- `pre-commit install` in a clone with `core.hooksPath` set printed ``[ERROR] Cowardly refusing to
  install hooks with `core.hooksPath` set.`` and ``hint: `git config --unset-all core.hooksPath` ``,
  exit 1. After the unset it printed `pre-commit installed at .git\hooks\pre-push`, exit 0.
  This repository's clone has `core.hooksPath=.agent-process/.githooks` in `.git/config`.
- A `repo: local` hook (`language: unsupported`, `always_run: true`, `pass_filenames: false`,
  `stages: [pre-push]`) with `default_install_hook_types: [pre-push]`: exit 0 → `Passed` and the
  push went through; exit 1 → `Failed`, `error: failed to push some refs`, `origin` unchanged.
  The entry ran with `bash` = `/usr/bin/bash` and cwd = the worktree root.
- Pushing from a linked worktree, git gave the hook
  `GIT_DIR=<clone>/.git/worktrees/<name>` (seen by a raw hook through `core.hooksPath`), and
  pre-commit passed it on to the entry unchanged; a `GIT_DIR` or `GIT_INDEX_FILE` exported by the
  caller also reached the entry. pre-commit does not clear the repository-local git environment;
  the current hook does (`pre-push:6-16`).
- A hook repository with this change's layout (`language: python`, the D5 `pyproject.toml`,
  console script `agent-process-quality`), run by `pre-commit try-repo <repo> quality
  --hook-stage pre-push` on Python 3.12.8: pre-commit built `py_env-python3` and ran the entry
  with that env's `Scripts` first on `PATH` and `VIRTUAL_ENV` set to it (also
  `PIP_DISABLE_PIP_VERSION_CHECK`), so `python` in the `bash -c` child resolved to the hook env.
  With that `Scripts` entry removed from `PATH` and `VIRTUAL_ENV` dropped when it equals the
  entry's `sys.prefix`, the child's `python` was the pusher's interpreter; the hook's exit 7
  reached pre-commit as `Failed`.
- `command -v python3` in the Bash tool resolves to `WindowsApps/python3`, the Store stub, not an
  interpreter.

## What Changes

- The publisher becomes a pre-commit hook repository: `.pre-commit-hooks.yaml` declares the hook
  `quality` (`language: python`, `stages: [pre-push]`), whose entry runs the declared `test` of the
  pushed checkout through `bash`, without the repository-local git environment. Without a
  declaration it prints that the push checked nothing and passes; a malformed one fails. The
  entry is a new mode of `skills/agent-process/scripts/quality.py`, the one parser of the
  declaration; `pyproject.toml` makes the repository pip-installable for pre-commit.
- `init` gains the step `pre-commit`: the marker-owned block of `.pre-commit-config.yaml` that
  references the hook at `rev: v<version>`; a fresh file also carries
  `default_install_hook_types: [pre-push]`. An existing file without the block is a `conflict`, as
  for Dependabot. The plan prints a `manual pre-push` row: per clone,
  `git config --unset-all core.hooksPath` where set, then `pre-commit install --hook-type pre-push`.
- This repository runs the same entry from its own commit through a `repo: local` hook and drops
  its bash hook. **BREAKING** for this repository's clones: until the per-clone step, a clone
  whose `core.hooksPath` still names the deleted directory runs no pre-push hook.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: *The installed footprint is closed* gains the block of `.pre-commit-config.yaml`;
  new *A push runs the declared test* and *Init renders the pre-push hook*.

## Impact

Added: `.pre-commit-hooks.yaml`, `.pre-commit-config.yaml`,
`skills/agent-process/templates/pre-commit-config.yaml`.

Edited: `skills/agent-process/scripts/quality.py`, `skills/agent-process/scripts/init.py`
(step, manual row, docstring), `skills/agent-process/SKILL.md` (Install step 4 names the
`pre-push` row), `pyproject.toml`, `release-please-config.json`,
`.agent-process/requirements-dev.in`, `.agent-process/requirements-dev.txt` (`pre-commit` for the
hook-repository test), `tests/publisher/test_quality.py`, `tests/publisher/init_harness.py`,
`tests/publisher/test_init_remote.py`, `tests/publisher/test_init_config.py`,
`tests/publisher/test_init_conflicts.py`, `tests/publisher/test_plugin.py`.

Removed: `.agent-process/.githooks/pre-push`, `.agent-process/.gitattributes` (its one rule
keeps that hook LF), `tests/agent_process/test_pre_push_hook.py`.

Reviewed and still true: `.agent-process/scripts/ci_check.py` `check_secrets` (the
`pre-push` it names now reaches `ci_check` through pre-commit) and
`.agent-process/scripts/hooks.py` (the Claude hooks adapter stays unrelated to the pre-commit
framework).

New consumer dependency: `pre-commit` on each machine that pushes. No ADR: design.md records
the decisions and alternatives. The *implementation* and *review-and-merge* requirements that
name the hook stay true: here the declared `test` is `ci_check`.
