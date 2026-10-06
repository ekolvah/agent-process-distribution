## Context

See proposal.md — Why for the reproduction and root cause. `hooks/hooks.json` keeps its
session-level gate (`cd "$CLAUDE_PROJECT_DIR"` and the adoption marker there); only the
directory `edit_lint.py` hands to `pre-commit` changes. The other plugin hooks do not read the
working directory, so they need no change.

## Goals / Non-Goals

**Goals:** a file is linted against the root and config of the repository that holds it; a file
outside an adopted repository is silent.

**Non-Goals:** linting files of other adopted repositories differently from the session's
project — any adopted repository holding the file is linted by its own config, which is the same
rule.

## Decisions

1. **Root = `git -C <file's directory> rev-parse --show-toplevel`, passed as `cwd=` of the
   `pre-commit` run.** That is the root pre-commit itself computes (`git.get_root()` in
   `main._adjust_args_and_chdir`); running from it makes pre-commit's `relpath` of the absolute
   file root-relative and loads that root's `.pre-commit-config.yaml`. Observed:
   `git -C <wt>/allowed rev-parse --show-toplevel` prints `<wt>` (proposal.md). `edit_lint` makes the
   path absolute first and uses that absolute path for both `git -C` (its directory) and
   `--files`, because pre-commit makes a relative `--files` entry absolute against its own
   working directory (`pre_commit/main.py`), which is now the file's root; so a relative
   `file_path` still resolves against the session's project as today.
   - Alternative: pass `--config <root>/.pre-commit-config.yaml` from the project directory.
     Rejected: pre-commit still `chdir`s to the working directory's root and makes the file
     `../…`, so root-anchored patterns still miss.
   - Alternative: change `hooks/hooks.json` to `cd` elsewhere. Rejected: the shell hook does not
     parse the payload; the file path is known only in Python.
2. **No repository → exit 0, no output.** `rev-parse` exiting non-zero (128 outside any
   repository, as observed) means the file is not repository code; there is nothing to lint and
   no degraded check to report, so §IV does not ask for a marker.
3. **Not adopted → exit 0, no output.** The root must carry `.github/workflows/agent-process.yml`,
   the marker `hooks/hooks.json` already reads for the session. Without this check a file of a
   non-adopted sibling repository would run that repository's `pre-commit` and could report its
   missing config as an error on every edit — the same noise class as #360.
4. **`git` joins `pre-commit` in the existing "not active" marker.** A `git` missing from `PATH`
   would otherwise raise `FileNotFoundError` (exit 1, which the agent never sees). One
   data-driven check over both names keeps the existing branch; the existing empty-`PATH` test
   covers it.

No new script or check is added; this corrects the directory of an existing one
([ADR 0034](../../../../.agent-process/docs/adr/0034-edit-time-lint-runs-the-projects-pre-commit-config.md)).
The guard dropped is none: the session-level gate stays, and the per-file adoption check is added.

## Risks / Trade-offs

- [One extra `git` process per edit (~tens of ms on Windows)] → negligible beside the ~0.5 s
  pre-commit start ADR 0034 records.
- [A worktree's branch config that is unstaged makes pre-commit fail with its own "configuration
  is unstaged" error] → that is pre-commit's standard behaviour in that root and reaches the
  agent as text, as in the main checkout today.

## Migration Plan

Ships in the next plugin release; no consumer action. Rollback is reverting the PR.
