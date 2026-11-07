## Context

`manual.pre_push` (`init`) and `templates/skill_check.py` `_pre_push` (session start) both return
the reason `core.hooksPath is set` from the exit code of `git config --get core.hooksPath` alone.
Both already resolve `git rev-parse --git-path hooks/pre-push` and join it to the clone root.
See proposal.md — Why.

## Standard approach

- git-config, `core.hooksPath` (https://git-scm.com/docs/git-config#Documentation/git-config.txt-corehooksPath):
  "Set this to different path … and Git will try to find your hooks in that directory". A
  relative path is "relative to the directory where the hooks are run" (githooks,
  https://git-scm.com/docs/githooks).
- Observed, git 2.45.1 in a scratch clone with `core.hooksPath=.githooks`:
  `git rev-parse --git-path hooks` printed `.githooks`, `--git-path hooks/pre-push` printed
  `.githooks/pre-push`, and from a subdirectory `--git-path hooks` printed `../.githooks`. So the
  path both modules already read resolves the configured directory.
- `git hook list <event>`, the standard way to enumerate hooks, does not exist in git 2.45.1:
  `git hook list pre-commit` printed `error: unknown subcommand: 'list'` and exited 129.
- pre-commit, repository-local hooks (https://pre-commit.com/#repository-local-hooks): a
  `repo: local` entry runs a script of the repository, which is the porting target the issue
  names. `pre-commit install` refuses while `core.hooksPath` is set (observation on record in
  the archived change `init-installs-pre-push-hook`, proposal — Why).

## Goals / Non-Goals

**Goals:** a person who follows the row or the marker learns, before unsetting
`core.hooksPath`, which hook files stop running.

**Non-Goals:** porting the hooks, unsetting `core.hooksPath`, or judging whether an entry is a
real hook.

## Decisions

**D1 — The directory is the parent of the resolved `hooks/pre-push` path.** Both modules read
`git rev-parse --git-path hooks/pre-push` already, and git resolves `core.hooksPath` there (see
Standard approach). The check therefore adds no git call. `skill_check._pre_push` reads it
before the `core.hooksPath` branch, as `manual.pre_push` already does.
Alternative: parse the `git config --get core.hooksPath` value and resolve it against the root.
Rejected, because that repeats git's own resolution.

**D2 — Entries are every name in that directory except `*.sample`, sorted.** `*.sample` is how
git ships disabled hooks. `git hook list` would be the standard, but the observed git lacks it.
Copying the githooks name list into two modules is bespoke and drifts with git. Over-reporting
a `README.md` costs one word of the row. A missing directory gives no entries. Any other
`OSError` is `Unreadable` in `manual` (printed `(cannot read: …)`) and a `cannot check` reason
in `skill_check` through its existing `_guarded`.

**D3 — A reworded reason, not a `conflict`.** With entries present, the reason becomes:
`core.hooksPath is set and <dir> holds <a>, <b>: git stops running them once it is unset, so port them to .pre-commit-config.yaml as repo: local hooks first`.
It replaces `core.hooksPath is set` in the row's parentheses and in the marker. `conflict` is
the classification of a consumer file `init` would overwrite, and it fails the whole run. But
`init` never touches git config, so nothing of this run is at risk. The hazard lies in the
person's next manual step, and the row that names that step now carries the warning. A second
row was rejected because each state gets one row.

**D4 — The two modules keep their own copy of the wording.** `skill_check.py` is a template
installed alone into consumers and cannot import `manual.py`. Each surface's tests assert the
directory, the entries and `repo: local`; no equality test like
`test_pre_push_id_matches_installer`, since no program reads the wording.

## Risks / Trade-offs

- [A hooks directory full of non-hook files makes a long row] → Accepted. Such directories are
  rare, and the row is read by a person.
- [An absolute `core.hooksPath` shared across repositories (for example `/etc/git/hooks`) is
  reported as this clone's] → Accepted. Unsetting it in this clone still stops those hooks here,
  which is exactly the warning.

## Migration Plan

Consumers get the new wording on their next `init` and their next session start after the
release. Nothing to migrate. Rollback is a revert of the PR.
