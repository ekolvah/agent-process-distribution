## Why

Edit-time lint is the cheapest feedback loop of a session: without it, a finding surfaces only
at the pre-push `quality` hook or in CI. Today ruff is declared twice in this repository, by
bespoke code each time: `ci_check.py` (`check_format`, `check_lint`) for the gate, and
`.agent-process/scripts/hooks.py on-edit`, wired in `.claude/settings.json`, for edit time.
ekolvah/kinozal_scraper keeps a third copy in `scripts/hooks.py`. Consumers get no edit-time
lint, and the implementation spec's "Shift-left feedback in Claude" names `ruff`, a linter the
plugin cannot assume in a mixed-stack consumer (#321, split from #313).

The industry standard declares per-file checks once, in `.pre-commit-config.yaml`, with the
hook repositories the tools publish, and lets every trigger read that file: the editor (here the
agent's `PostToolUse` hook, as in the hooks guide's "Auto-format code after edits") and CI
(`pre-commit run --all-files`). The plugin only needs to trigger it after each edit.

Observed on 2026-10-02 with pre-commit 4.6.0:

- `pre-commit run --hook-stage pre-commit --files README.md` in this repository, whose only hook
  is `stages: [pre-push]`, printed nothing and exited 0 in 0.5 s.
- A finding exits 1 with the hook's report on stdout; an absolute Windows path and a path outside
  the repository are both accepted and linted. A missing `.pre-commit-config.yaml` exits 1 with
  `InvalidConfigError: ... is not a file`.
- `ruff-format` rewrites the file. For a tracked file pre-commit reports `files were modified by
  this hook` and exits 1; for an untracked file it reports `Passed`. On the next turn the harness
  reported the file "changed on disk", and an `Edit` against the rewritten content succeeded
  without a re-`Read`.
- The first run with an empty `PRE_COMMIT_HOME` took 13.5 s to install the hook environment, more
  than the 10 s timeout of the existing plugin hooks. The hooks reference: Claude Code "cancels a
  `command` ... hook that reaches its `timeout`, discarding the hook's output".
- A `pre-push` hook whose entry is `pre-commit run --hook-stage pre-commit --all-files
  --show-diff-on-failure` (scratch repository) printed `ruff-check`'s finding and `ruff-format`'s
  diff and exited 1: a nested run works.
- In this repository `astral-sh/ruff-pre-commit` `v0.15.12` (`ruff-check`, `ruff-format
  --check`) over `--all-files` passed in 1 s, as `ci_check` does at the same head. The
  `[tool.ruff]` sections of `pyproject.toml` and `.agent-process/pyproject.toml` are identical,
  so ruff's per-file config discovery gives the verdict of `ci_check`'s explicit `--config`.
- `.agent-process/requirements*.txt` hold top-level pins only, not `pip-compile` output; pip-tools'
  `pip-compile` hook would rewrite them, so it is not adopted.

## What Changes

- New package script `skills/agent-process/scripts/edit_lint.py` (`agent-process edit_lint
  post-edit`): runs `pre-commit run --hook-stage pre-commit --files <edited path>` and feeds a
  failure's output back to the agent with exit 2. A payload without a path is silent; a missing
  `pre-commit` is a visible marker (§IV). The plugin knows no linter.
- `hooks/hooks.json` gains a second `PostToolUse` `Edit|Write` hook running it, behind the
  adoption gate, with a timeout that covers a first environment install.
- This repository declares ruff once: `ruff-check` and `ruff-format` of
  `astral-sh/ruff-pre-commit` at the `pre-commit` stage of `.pre-commit-config.yaml`.
- `ci_check.py` runs that declaration: `format` and `lint` become one `lint` check running
  `pre-commit run --hook-stage pre-commit --all-files --show-diff-on-failure`, and `ruff` leaves
  `requirements-dev`, so the hook's `rev` is its only pin.
- `.agent-process/scripts/hooks.py`, its tests and the `PostToolUse` entry of
  `.claude/settings.json` are deleted, with the `requirements*.in` reminder (`check_requirements`
  still catches drift).
- SKILL.md Install names edit-time lint and how a project's gate runs the same checks; ADR 0034
  records the practice, in line with ADR 0027.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: the plugin ships edit-time lint through the project's pre-commit config; the
  memory checkpoint requirement's clause on this repository's post-edit hook reads the settings,
  since `hooks.py` is deleted.
- `implementation`: `ci_check` runs the `pre-commit`-stage hooks; "Shift-left feedback in Claude"
  and "A broken hook is visible" name those hooks instead of `ruff`.

## Impact

- Added: `skills/agent-process/scripts/edit_lint.py`, `tests/publisher/test_edit_lint.py`,
  `.agent-process/docs/adr/0034-edit-time-lint-runs-the-projects-pre-commit-config.md`.
- Edited: `hooks/hooks.json`, `.pre-commit-config.yaml`, `.agent-process/scripts/ci_check.py`,
  `.agent-process/requirements-dev.in`, `.agent-process/requirements-dev.txt`,
  `.claude/settings.json`, `skills/agent-process/SKILL.md` (Install),
  `tests/publisher/test_plugin.py`, `tests/publisher/test_start_change.py` (`MOVED_SCRIPTS`),
  `tests/agent_process/test_ci_check.py`, `tests/agent_process/test_delivery_gate_wiring.py`
  (docstring names the deleted test file).
- Removed: `.agent-process/scripts/hooks.py`, `tests/publisher/test_hooks.py`.
- CI: the check matrix loses its `format` job; the required context is `agent-process /
  quality` alone. The `lint` job installs the ruff hook environment on each run.
- Consumers: after the release, an adopted repository's `pre-commit`-stage hooks run after each
  edit; one with none declared (the `init` template declares only `quality` at `pre-push`) sees
  nothing. kinozal_scraper moves its ruff into its config and deletes its copy in
  ekolvah/kinozal_scraper#614.
