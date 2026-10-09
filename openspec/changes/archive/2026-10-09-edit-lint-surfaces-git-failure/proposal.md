## Why

`edit_lint.adopted_root` reads every non-zero exit of `git rev-parse --show-toplevel` as "not
repository code", so a git failure inside a real repository — dubious ownership (common on
Windows for a clone made by another user or tool), an unsupported or corrupt repository —
skips edit-time lint with exit 0 and no output (§IV: a silent skip instead of a marker).

Reproduction (git 2.45.1.windows.1, `git -C <dir> rev-parse --show-toplevel`, all exit 128):

| Case | stderr |
|---|---|
| directory in no repository | `fatal: not a git repository (or any of the parent directories): .git` |
| `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` in a repository | `fatal: detected dubious ownership in repository at '<root>'` plus the `safe.directory` hint |
| `extensions.zzz = true` at format version 1 | `fatal: unknown repository extension found:` / `zzz` |
| `.git` file pointing at a missing gitdir (a removed worktree) | `fatal: not a git repository: <gitdir>` |
| directory inside `.git/` (`.git`, `.git/hooks`) | `fatal: this operation must be run in a work tree` |

Root cause: the exit code is the same for all five; only git's stderr tells "no repository
found" or "inside a git directory" apart from "a repository git refuses or cannot read". The failing test is the new
scenario's test: today the second and third cases exit 0 with no output.

## What Changes

- The hook exits 0 silently only when git reports that it found no repository or that the
  file is inside a git directory; any other `rev-parse` failure exits 2 with
  `edit-time lint is not active: <git's stderr>`.
- git runs with `LC_ALL=C` and without `LANGUAGE`, so that the message it is classified by is
  not translated.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: requirement "The plugin ships edit-time lint" gains the git-failure marker
  and its scenario.

## Impact

- Edited: `skills/agent-process/scripts/edit_lint.py`, `tests/publisher/test_edit_lint.py`,
  `openspec/specs/distribution/spec.md` (by the archive).
- ADR 0034 does not change: its decision (per-file checks declared once in
  `.pre-commit-config.yaml`) stands; which failures are markers is the spec's.
