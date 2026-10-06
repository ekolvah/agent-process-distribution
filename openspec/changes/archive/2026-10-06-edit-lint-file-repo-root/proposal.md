## Why

The plugin's `edit_lint` hook reports false findings, and checks against the wrong rules, for
a file outside the checkout `$CLAUDE_PROJECT_DIR` names: a file of a git worktree
(`.claude/worktrees/<name>/…`) and a file outside any repository (the session scratchpad
holding a PR body). Observed on plugin 3.8.4 about five times in one session (#360); each is
noise the agent must dismiss, and a real finding hides in it.

**Reproduction** (pre-commit 4.6.0; a repository whose `pygrep` hook excludes `^allowed/`, and
`git worktree add ../wt`):

- From the main checkout, `pre-commit run --hook-stage pre-commit --files <abs>/wt/allowed/x.md`
  → `Failed`, `../wt/allowed/x.md:1:FORBIDDEN`, exit 1.
- The same command from `<abs>/wt` → `(no files to check)Skipped`, exit 0.
- From the main checkout, `--files <abs>/out.md` (no repository) → `Failed`, `../out.md:1:…`, exit 1.
- `git -C <outside dir> rev-parse --show-toplevel` → `fatal: not a git repository`, exit 128;
  `git -C <abs>/wt/allowed rev-parse --show-toplevel` → `<abs>/wt`.

**Root cause.** `hooks/hooks.json` runs `edit_lint` in `$CLAUDE_PROJECT_DIR`, and
`edit_lint.py` runs `pre-commit` in that working directory. pre-commit's
`main._adjust_args_and_chdir` takes `git.get_root()` of the working directory, `chdir`s there,
and rewrites each `--files` path with `os.path.relpath`, then reads `.pre-commit-config.yaml`
from that root. So a worktree or outside file becomes `../…` or `.claude/worktrees/<name>/…`,
a root-anchored `files`/`exclude` no longer matches, and a worktree is checked against the main
checkout's config, not its branch's.

## What Changes

- `edit_lint` runs `pre-commit` from the root of the git repository that holds the edited file
  (`git -C <file's directory> rev-parse --show-toplevel`); in a worktree that root is the
  worktree, so its own config and root-relative paths apply.
- A file in no git repository, or in a repository without `.github/workflows/agent-process.yml`,
  gets no lint and no output.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: requirement "The plugin ships edit-time lint" runs `pre-commit` in the edited
  file's repository root and is silent for a file outside an adopted repository.

## Impact

- Edited: `skills/agent-process/scripts/edit_lint.py` (root resolution, adoption check, docstring).
- Edited: `tests/publisher/test_edit_lint.py` (worktree, outside-file, not-adopted and branch-config tests).
- Edited: `tests/publisher/lint_harness.py` (`lint_repo` writes the adoption marker and commits, so a worktree can be added).
- Edited: `tests/publisher/test_plugin.py` (drops the marker write that `lint_repo` now does).
- Edited: `.agent-process/docs/adr/0034-edit-time-lint-runs-the-projects-pre-commit-config.md` (the run's directory is the edited file's repository root).
- Added: `openspec/changes/edit-lint-file-repo-root/` (this change); archived into `openspec/specs/distribution/spec.md`.
- `hooks/hooks.json` is unchanged: its session-level adoption gate stays.
