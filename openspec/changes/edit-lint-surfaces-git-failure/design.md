## Context

See proposal.md — Why for the reproduction. `adopted_root` runs
`git -C <dir> rev-parse --show-toplevel` and maps every non-zero exit to "nothing to lint".
git exits 128 both when discovery finds no repository and when it finds one it will not read,
so the exit code cannot separate them.

## Goals / Non-Goals

**Goals:** a `rev-parse` failure is silent only when git found no repository or the file is
inside a git directory.

**Non-Goals:** diagnosing or repairing the repository (git's own message carries the
`safe.directory` hint); detecting adoption of a repository git cannot read.

## Decisions

1. **Classify by git's discovery message, prefix `not a git repository (or any `.** Discovery
   gives up with one of two `die` calls of `setup_git_directory_gently()` in git v2.45.1
   `setup.c`: `not a git repository (or any of the parent directories): %s`
   (`GIT_DIR_HIT_CEILING`) and `not a git repository (or any parent up to mount point %s)`
   (`GIT_DIR_HIT_MOUNT_POINT` — a scratchpad on its own mount). The prefix matches both and not
   `not a git repository: <gitdir>`, which git prints for a `.git` file naming a missing
   directory: a removed worktree is a repository git cannot read, and it gets the marker.
   Alternatives: substring `not a git repository` — silences the broken-worktree case;
   walking parents for `.git` ourselves — re-implements git's discovery (ceilings,
   `GIT_DIR`, gitfiles) and still cannot tell why git refused.
2. **A file inside a git directory is silent: `fatal: this operation must be run in a work
   tree`.** Observed (git 2.45.1.windows.1, `git -C <repo>/.git rev-parse --show-toplevel` and
   the same for `.git/hooks`, exit 128); for `rev-parse --show-toplevel` it is raised in `builtin/rev-parse.c` when there is no work tree.
   An edit of `.git/info/exclude` or a hook is not repository code, and a marker on every such
   edit is one the agent cannot act on. Alternative: marker — rejected for that noise.
3. **Run git with `LC_ALL=C` and `LANGUAGE` removed.** The messages are translated (`_()`
   above); on a localized Linux or macOS the prefixes would not match and every edit outside a
   repository would raise a false marker. POSIX XBD 8.2: "The value of the LC_ALL environment
   variable has precedence over any of the other environment variables starting with LC_";
   `LANGUAGE` is a GNU extension outside that rule, so it is dropped rather than relied on.
   Alternative: match translations too — unbounded.
4. **Any other failure is a marker, adopted or not.** git refused before the adoption marker
   could be read, so the hook cannot know; a false marker on a non-adopted repository is
   visible and actionable, a false silence is neither (§IV). Marker:
   `edit-time lint is not active: <git's stderr>`, exit 2, as the existing markers.
5. **Capture check first.** The `stdout`/`stderr is None` check moves before the exit-code
   branch, since the failure branch now reads `stderr` (repository convention: a `None` is
   not an empty string).
6. **Test doubles are real git states**, no mock: `GIT_TEST_ASSUME_DIFFERENT_OWNER=1` drives
   git's own dubious-ownership path (observed on 2.45.1.windows.1; present since 2.35.2), an
   `extensions.zzz` at format version 1 the unknown-extension path, and a `.git` file naming a
   missing directory the gitfile path; a file under `.git/` is the work-tree case of
   decision 2. The environment variable reaches git through the hook's environment, as
   `safe.directory` state would.

## Risks / Trade-offs

- [A future git rewords the discovery message] → every edit outside a repository shows the
  marker: loud, not silent, and the test of the no-repository case fails on that git.
- [Invalid `HEAD` in a repository] → git's discovery skips it and reports no repository
  (observed: `echo garbage > .git/HEAD` gives the parent-directories message), so it stays
  silent; git itself does not treat it as a repository. Accepted.
- [`core.bare=true` set by mistake in a checkout] → git prints the work-tree message of
  decision 2 for its files too, so edit-time lint is silent there. Accepted: every git command
  in that checkout fails the same way, so the misconfiguration is visible outside the hook.
- [Locale pinning has no test] → the local git for Windows printed English under
  `LANG=ru_RU.UTF-8`, and every job of `.github/workflows/quality.yml` runs on `ubuntu-latest`
  without generating a non-English locale or installing git's catalogue, so a translated-run
  test would pass whether or not the pin exists. Decision 3 rests on the cited POSIX rule.

## Migration Plan

None: plugin code only. Rollback is reverting the PR.
