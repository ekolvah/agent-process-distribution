## Why

`check_red` runs pytest in the change's worktree, and every Python process of that run
writes bytecode next to the sources it imports. In a consumer without an ignore rule for
`__pycache__` (issue 250: `ekolvah/agent-process-sandbox-2`, installed by `init.py`, no
`.gitignore`) the first RED run leaves the worktree dirty, so `archive_change` refuses to
archive (`git status --porcelain` non-empty, `archive_change.py:87`) and `start_change` keeps
the merged worktree instead of removing it (`start_change.py:156`).

Reproduction, 2026-09-29 (Python 3.12, pytest 9.0.3): a fresh git repository with
`pkg/__init__.py`, a failing `tests/test_f.py` and a quality declaration, no `.gitignore`;
`check_red.py tests/test_f.py::test_f` prints `RED: 1 failed, 0 green (of 1 tests)` and
`git status --porcelain` then prints `?? pkg/__pycache__/` and `?? tests/__pycache__/`. The
same run with `PYTHONDONTWRITEBYTECODE=1` in the environment leaves `git status --porcelain`
empty. pytest's assertion rewriter honours the same switch: `_pytest/assertion/rewrite.py`
line 173, `write = not sys.dont_write_bytecode`. The run already keeps its cache and its report
out of the tree (`-o cache_dir=<tmp>`, `--junitxml=<tmp>`); bytecode is the one write left.

## What Changes

- `check_red` runs pytest with bytecode writing switched off for that run and every Python
  process it starts, so the gate leaves the working tree as it found it.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: *RED first for behavioural changes* — `check_red` leaves no file in the
  working tree.

## Impact

- Edited: `skills/agent-process/scripts/check_red.py` (the child environment, the module
  docstring's configuration sentence), `tests/publisher/test_check_red.py` (one live test and
  the module docstring's "pytest itself is not spawned" sentence).
- No ADR: the decision is local to the script and recorded in `design.md`; ADR 0027 already
  deleted the `.gitignore` entry that existed only to hide this script's report, and this
  change follows it.
- Not changed: the consumer's own `test` command and its ignore rules (`design.md` —
  Non-Goals).
