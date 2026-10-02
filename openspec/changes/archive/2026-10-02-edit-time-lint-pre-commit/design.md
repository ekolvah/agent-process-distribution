## Context

See proposal.md, Why, for the observations this design rests on. The archived changes
`2026-10-02-ship-navigation-hooks` and `2026-10-02-ship-memory-checkpoint` set up the
mechanism this change reuses: plugin hooks in `hooks/hooks.json`, each calling a package script
through `bin/agent-process` behind the adoption gate `.github/workflows/agent-process.yml`, and
the requirement "Plugin hooks act only in adopted repositories" over every hook command.

`.agent-process/scripts/hooks.py` holds only the ruff check and the `requirements*.in`
reminder (#322).

## Goals / Non-Goals

**Goals:**
- Per-file checks declared once, in `.pre-commit-config.yaml`, read by the edit-time trigger and
  by the gate.
- Edit-time lint in every adopted consumer, from checks the project declares itself.
- This repository dogfoods both and loses its bespoke post-edit hook and its own ruff calls.

**Non-Goals:**
- Installing the git `pre-commit` hook (`default_install_hook_types` stays `[pre-push]`, open
  decision of #321): only agents write code in an adopted repository; the edit-time run is their
  per-file feedback, and push and CI are the gate.
- The plugin's `quality.yml` running pre-commit for consumers: a consumer's declared `test`
  decides what its gate runs; SKILL.md Install says how to include the same checks (D7).
  kinozal_scraper does so in ekolvah/kinozal_scraper#614.
- pip-tools' `pip-compile` hook (proposal, Why).
- Telling scratch files from project files: a path outside the repository is linted with the
  project's config, as `hooks.py` does today.

## Decisions

### D1. A package script, `edit_lint.py`

`skills/agent-process/scripts/edit_lint.py`, `main` taking `post-edit`, reads the hook JSON on
stdin (UTF-8, as `memory_checkpoint.py`) and takes `tool_input.file_path`.

- No path, an empty or malformed payload → exit 0, no output (a payload bug must not red every
  edit).
- `shutil.which("pre-commit")` is `None` → stderr `edit-time lint is not active: pre-commit is
  not on PATH`, exit 2.
- Otherwise run `[pre-commit, "run", "--hook-stage", "pre-commit", "--color", "never", "--files",
  path]` with `capture_output=True, encoding="utf-8", errors="replace"`. A `None` stream is a
  marker naming the failed capture, exit 2 (AGENTS.md: no `None` turned into `""`).
- Exit 0 → no output. Any other exit → stdout and stderr of the run to stderr, exit 2.
  pre-commit exits 1 both for findings and for its own errors (proposal, Why); both reach the
  agent as text, so the script does not tell them apart.
- Unknown subcommand → usage, exit 2, as the other hook scripts.

**Problem and standard (SKILL.md Design).** The problem: lint runs only at push or in CI, and
the existing edit-time check is bespoke, ruff-only and undelivered (#321). The standard for the
checks is pre-commit with published hook repositories; the standard for the trigger is a Claude
Code `PostToolUse` hook. The script is the glue the hooks guide writes as `jq -r
'.tool_input.file_path' | xargs ...`: `jq` is not on every consumer's machine, and a bare pipe
cannot map "pre-commit missing" to a marker or the run's exit to exit 2.

Alternatives:
- `edit_check` key in `.github/agent-process-quality.json` (#313's first ask). Rejected: a second,
  bespoke list of checks beside the one pre-commit already reads.
- Ship `hooks.py`. Rejected: it hardcodes ruff.
- `python -m pre_commit` of the launcher's interpreter. Rejected: pre-commit is the person's
  install (pipx, a venv, the system), not the launcher's; `init` checks the same `PATH`.
- Gate on `.pre-commit-config.yaml` existing. Rejected: `init` writes it in every adopted
  repository; when it is gone pre-commit's own `InvalidConfigError` reaches the agent, which is
  the visible degradation §IV asks for.

### D2. A second hook in the `PostToolUse` `Edit|Write` group, timeout 120

The existing `Edit|Write` group of `hooks/hooks.json` gets a second hook object, command
`cd "$CLAUDE_PROJECT_DIR" && { [ ! -f .github/workflows/agent-process.yml ] || sh "${CLAUDE_PLUGIN_ROOT}/bin/agent-process" edit_lint post-edit; }`,
`timeout: 120` (the timeout is per hook object, as the memory checkpoint's `10`). The hooks
reference: "All matching hooks run in parallel", so the memory checkpoint and the lint run side
by side. The 10 s of the other hooks is below the observed 13.5 s first install, and a timeout
discards the output silently. 120 s covers a first install of a typical hook environment; a
later run takes about 0.5–2 s.

### D3. Formatters may rewrite the file

The plugin does not forbid a mutating hook. The hooks guide shows `prettier --write` as the
canonical `PostToolUse` example, and the observation in the proposal shows the harness reporting
the rewrite and the next `Edit` succeeding. `hooks.py` avoided `ruff format` without `--check`
on the assumption that a rewrite breaks the next `Edit`; the observation refutes it. A tracked
file that a formatter rewrites still exits 1 (`files were modified by this hook`), so the agent
also hears about it.

### D4. This repository declares ruff once, with `astral-sh/ruff-pre-commit`

`.pre-commit-config.yaml` gains, before the local `quality` repository:

```yaml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff-check
        stages: [pre-commit]
      - id: ruff-format
        stages: [pre-commit]
```

`ruff-check` without `--fix`: a fix can delete code the agent is about to use. `ruff-format`
rewrites at edit time (D3); under `ci_check` a rewrite fails the run (`files were modified`) and
`--show-diff-on-failure` prints the diff, so it is also the format check. `stages:
[pre-commit]` keeps the hooks out of a plain pre-push run, where `quality` reaches them through
`ci_check` (D5). `v0.15.12` is today's `requirements-dev.txt` pin; `ruff` leaves
`requirements-dev.in` and `.txt`, so the `rev` is the only ruff pin and `pre-commit autoupdate`
bumps it (this repository has no Dependabot configuration, so no automatic bump is lost).

Alternative: local hooks `python -m ruff ...` (`language: unsupported`). Rejected: a
hand-written hook definition for what the ruff project publishes, and it keeps ruff in
`requirements-dev`.

Ruff discovers its config from the file's path: `.agent-process/**` gets
`.agent-process/pyproject.toml`, the rest the root `pyproject.toml`. Their `[tool.ruff]` sections
are identical (proposal, Why), so dropping `ci_check`'s explicit `--config` changes no verdict.

### D5. `ci_check` runs the `pre-commit`-stage hooks

`check_format` and `check_lint` become one `check_lint`:
`_run([sys.executable, "-m", "pre_commit", "run", "--hook-stage", "pre-commit", "--all-files",
"--show-diff-on-failure"])`. `pre-commit` is in `requirements-dev`, which the declared `setup`
installs, so `python -m pre_commit` is the gate's own interpreter, as every other check.

- `--hook-stage pre-commit` excludes `quality` (`pre-push`), so the pre-push run of `ci_check`
  does not recurse; the nested run is observed (proposal, Why).
- The product-scope split of format and lint goes: pre-commit lists tracked files and ruff
  picks the config per file. `_has_product_scope` and `_product_scope_excludes` stay for
  pytest and module size.
- The gate's lint scope narrows from the filesystem walk of `ruff check .` to tracked files
  (`git ls-files`). An untracked `.py` is still linted at edit time (`--files <path>` takes
  it, proposal, Why), and every file a push carries is tracked. `_find_modules` keeps
  untracked files for mypy and module size.
- The gate's format step stops being read-only: `ruff-format` rewrites unformatted tracked
  files, and with `--all-files` pre-commit stashes nothing. A rewrite fails the run with the
  diff; the agent commits only the files of its own change and leaves any other rewritten file
  as it found it.
- The registry loses `format`; `ci_check --list` and the CI matrix follow. Branch protection
  requires `agent-process / quality` only.
- Tests: `test_bare_format_pass_excludes_the_process_paths` and
  `test_bare_lint_pass_excludes_the_process_paths` go with the behaviour. The complexity tests
  (`C901`, `RUF100`) copy this repository's `.pre-commit-config.yaml` into their temporary
  repository beside the process `pyproject.toml` and keep asserting through `check_lint`.

The edit-time hook therefore runs a subset of the gate, from the same file.

### D6. This repository drops `hooks.py`

`.agent-process/scripts/hooks.py`, `tests/publisher/test_hooks.py` and the `PostToolUse` entry
of `.claude/settings.json` go. The memory-checkpoint requirement's clause and scenario on this
repository's own post-edit hook now read the settings: they declare no `PostToolUse` hook.

Dropping the guard: failure modes and the catcher reached for each lost proof.
- **The ruff check of an edited `.py` file.** Caught after merge by the plugin's lint hook at
  the first edit once the release reaches this machine. Before that, and on a machine without
  the plugin: `ci_check` `lint` (D5) at the pre-push `quality` hook on every pushed head, and
  the `agent-process / quality` check on the PR head.
- **The `requirements*.in` reminder.** Caught by `ci_check.py` `check_requirements`, which
  fails with `Run: pip-compile <file>` on lockfile drift, at pre-push and on the PR head.
- **`ruff` missing from the session's `python`.** Gone as a failure mode: pre-commit installs
  ruff into the hook environment. A missing `pre-commit` is D1's marker.
- **Platform does not dispatch the plugin's `PostToolUse` hooks.** Uncaught by the suite, which
  runs the command through `sh -c`; the same residual as the memory checkpoint's D5, whose hook
  shares this group. Noticed at the first `.py` edit with a finding after the release; until
  then the pre-push `quality` hook and the PR check lint every head.

### D7. Install and ADR

SKILL.md Install gains one sentence after the memory checkpoint: after each edit the plugin runs
the project's `pre-commit`-stage hooks on the edited file and shows a failure to the agent;
declare per-file linters there (the template declares none), and have the declared `test` run
`pre-commit run --hook-stage pre-commit --all-files` so the gate runs the same checks. ADR 0034
records the practice (per-file checks declared once in `.pre-commit-config.yaml`; the plugin's
edit-time hook and the gate are its triggers; no git `pre-commit` hook, since only agents write
code) with *Native alternatives considered* (D1) and its *Deletion condition*: Claude Code runs
pre-commit after edits natively, or pre-commit gains an editor/agent hook mode that a plugin can
enable without a script.

## Risks / Trade-offs

- [A first hook-environment install longer than 120 s is cut and its output discarded, with no
  marker.] → Accepted: the next edit runs pre-commit again, and the gate still lints.
- [Each CI `lint` job, the CI `pytest` job (the complexity tests run `check_lint` in a
  temporary repository with this config) and a first local suite run install the ruff hook
  environment from the network (13.5 s cold).] → Accepted; caching `~/.cache/pre-commit` is a
  later optimisation of `quality.yml`.
- [At pre-push, `ruff-format` rewrites unformatted tracked files across the whole checkout,
  including another session's uncommitted file in a shared checkout, and the push fails.] →
  Accepted: the standard pre-commit behaviour, and a rewrite only formats. Changes are pushed
  from their own worktree (`start_change`); the diff is in the output, and the agent commits only
  the files of its own change (D5).
- [Linting a file in another git worktree uses the project directory's config.] → Accepted: the
  same as `hooks.py`; ruff still reads the file's own `pyproject.toml`.
- [Every edit of a project without `pre-commit`-stage hooks spends one ~0.5 s pre-commit
  start.] → Accepted: observed cost; output is empty.
- [kinozal_scraper declares no `pre-commit`-stage hook, so the plugin's hook is silent there and
  its own `hooks.py` keeps linting until kinozal_scraper moves ruff into its config and deletes
  the copy.]
  → Tracked in ekolvah/kinozal_scraper#614.
- [A machine on a release older than this change has no edit-time lint in this repository until
  auto-update.] → Accepted, the window of the memory checkpoint's D5; the gate covers it.

## Migration Plan

Release through release-please; machines get it with the plugin's auto-update. No `init` step:
plugin hooks need no project setting, and the template's config is unchanged. Rollback is a
revert PR and the next release, which restores `hooks.py`, its settings entry, ruff in
`requirements-dev` and the two ruff checks of `ci_check`.
