## Context

See proposal.md — Why for the reproduction. `check_red` already chooses its own configuration
for the run (`--maxfail=0`, `-p no:stepwise`, `-o cache_dir=<tmp>`, `--junitxml=<tmp>`) and
spawns it with `subprocess.run` without an `env`, so the child inherits the caller's
environment unchanged.

## Goals / Non-Goals

**Goals:**
- The gate's run writes nothing into the working tree, whatever the consumer ignores.

**Non-Goals:**
- The consumer's own `test` command (Verify) and the implementer's ad-hoc pytest runs: they
  are the project's configuration, and a Python project that runs them without ignoring
  `__pycache__` gets the same untracked files from any tool. `archive_change` names every
  untracked path when it refuses, so that case stays visible, not silent.
- The clean-worktree guards of `archive_change` and `start_change` stay as they are.

## Decisions

**D1 — `PYTHONDONTWRITEBYTECODE=1` in the child environment.** `check_red` passes
`env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}` to its `subprocess.run`. The variable
sets `sys.dont_write_bytecode` in pytest's interpreter, which stops both the import system's
`.pyc` files and pytest's rewritten-assertion cache (proposal — Why), and it is inherited by
every Python process a test starts, so the gate's whole run is covered, not only the first
interpreter.

Alternatives:
- `python -B -m pytest`: the same switch, visible in the command, but it binds only the first
  interpreter; a test that spawns `python script.py` would still write bytecode.
- `PYTHONPYCACHEPREFIX=<tmp>`: redirects instead of suppressing; the temporary directory is
  deleted after the run anyway, so the redirect buys nothing over not writing.
- A managed `.gitignore` fragment from `init.py`: writes a consumer file for a script's side
  effect — the convention ADR 0027 deleted for the report path.
- `git status --porcelain --untracked-files=no` in `archive_change` and `start_change`: drops
  the guard; a new source or test file forgotten outside the commit would no longer stop the
  archive, and the pushed head would miss it. Nothing else catches that before the PR.
- `.git/info/exclude` written by `start_change`: per-clone state no one sees, and the gate
  would still write into the tree.

**D2 — The test is live.** The observable is `git status --porcelain` of a real repository
after a real pytest run; a faked `subprocess.run` can only check that the variable was passed,
which is the mechanism, not the outcome. One test in `tests/publisher/test_check_red.py`
builds a git repository in `tmp_path` (package, failing test, quality declaration, no
`.gitignore`), removes `PYTHONDONTWRITEBYTECODE` from the test's own environment so an outer
setting cannot make it pass, runs `check_red.main` from there, and asserts the RED exit and an
unchanged `git status --porcelain`. The assertion covers every file the run could leave
(bytecode, `.pytest_cache`, the report), not only `__pycache__`.

## Risks / Trade-offs

- [No bytecode cache → each gate run recompiles the imported modules] → the gate runs a
  handful of node ids; the cost is the compile time of those modules, paid once per run.
- [A consumer test that asserts on written `.pyc` files fails under the gate for that reason
  alone, a false RED] → none is known; the GREEN run under the project's own `test` command
  still writes bytecode, so such a test cannot stay red unnoticed past Verify.

## Migration Plan

None: the next plugin release carries the script. Rollback is the revert of the one-line
`env=`.
