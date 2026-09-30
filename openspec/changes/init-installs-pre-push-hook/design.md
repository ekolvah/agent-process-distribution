## Context

`init` renders the `quality` hook into `.pre-commit-config.yaml` (#188) and leaves installing
it to a `manual pre-push` row that `manual.py` prints while `_pre_push` does not observe this
clone's hook (no `core.hooksPath`, hook carries pre-commit's `# ID:` line). Observations of
`pre-commit install --hook-type pre-push` are in proposal.md — Why.

## Goals / Non-Goals

**Goals:** the clone `init` runs in ends a confirmed run with the hook installed whenever
nothing shared stands in the way; every other clone gets a visible marker at session start.

**Non-Goals:** touching `core.hooksPath` or any shared git config; installing the hook in
clones other than the current one; checking that the installed hook actually runs (the
`quality` hook's own tests cover that).

## Decisions

### D1. One reader of the clone's state, used by the step and the row

`manual.py`'s `_pre_push` becomes the one reader, returning the clone's state: installed,
installable, or blocked with a reason (`core.hooksPath is set`, `pre-commit is not on PATH`);
a read that fails raises `Unreadable`, as today. `manual.Target` gains the resolved `pre-commit`
executable (`None` when `shutil.which` finds none). The `init` step maps installed →
`unchanged`, installable → `planned`, blocked or unreadable → no step; the row is printed only
for blocked (with the reason) or unreadable (`(cannot read: …)`). One reader keeps the row and
the transition from disagreeing about the same clone.

*Alternative:* keep the row for every clone without a hook, as a reminder for other clones.
Rejected: in a dry-run it would duplicate the planned line, and after a confirmed run it would
be false for this clone; other clones get the session-start marker (D4).

### D2. The step runs last and is not a consumer-file change

The `pre-push` step is appended after `onboarding-pr` and is left out of the `planned` test
that decides whether onboarding steps exist. Last, so the installation branch's own push runs
no hook: that push would otherwise build the hook repository's environment over the network and
run a declared test the installation cannot yet satisfy. Outside `planned`, so a clone whose
files are already current (a second clone, a rerun after merge) gets its hook without a branch,
commit, issue or PR.

`apply` re-reads the state (installed → not written), runs `pre-commit install --hook-type
pre-push` through `ctx.call` with `cwd=ctx.root` (non-zero → `InstallError`, exit 1), and reads
the state again: not installed is an `InstallError` naming the hook path, never a silent
`written` (§IV).

`pre-commit install` also creates its cache (`.lock`, `db.db`, `README`) under
`~/.cache/pre-commit`, a user-profile write the closed footprint forbids (observed
2026-09-30 with pre-commit 4.6.0 during implementation). The call therefore sets
`PRE_COMMIT_HOME` to a temporary directory removed afterwards; the hook it writes is the same
and does not name the cache (observed), and the hook finds pre-commit's default cache when it
runs.

### D3. A foreign hook is left to pre-commit's migration mode

An existing pre-push hook that pre-commit did not install is classified `planned`;
`pre-commit install` keeps it as `pre-push.legacy` (observed). The step's detail names that when
such a hook exists, so the dry-run shows it before the person confirms. *Alternative:* treat a
foreign hook as blocked. Rejected: pre-commit's standard migration preserves the hook; a
bespoke refusal adds a manual step for no observed problem.

### D4. The session-start check carries the gap for other clones

`templates/skill_check.py` (installed as `.claude/agent-process-check.py`) is the only code that
runs in every clone without the person asking, so it is the carrier. It gains a second verdict:
when `$CLAUDE_PROJECT_DIR/.pre-commit-config.yaml` carries the `# agent-process:begin` line, it
reads `git config --get core.hooksPath` (exit 0 → reason `core.hooksPath is set`; other than 0
or 1 → cannot check) and `git rev-parse --git-path hooks/pre-push`, and marks the hook missing
when that file lacks the ID line. It stays self-contained (the consumer has no `manual.py`), so
it carries its own copy of the ID constant; a test pins it equal to `manual.PRE_COMMIT_ID`.
Git calls capture with `encoding="utf-8"` and a timeout, as the `claude` call does.

The hook emits one JSON object, so both verdicts share it: `systemMessage` joins the markers
with a newline, `additionalContext` with a space, each marker keeping its own advice. The
pre-push marker's fix is the two commands, not the Install URL. Any exception in the pre-push
verdict becomes its `cannot check` reason without suppressing the skill verdict.

Problem closed: the silent gap the archived `consumer-pre-push-hook` design accepted (#270).
Standard for the job: pre-commit has no command that reports whether a clone's hook is
installed (`pre-commit --help`, 4.6.0: `install`, `uninstall`, `init-templatedir`, … and no
status); its `init-templatedir` with `git config init.templateDir` installs the hook in future
clones only, and through machine-wide git config that every repository shares — the kind of
shared-state change this change keeps out of scope. *Alternative:* a new standalone hook script.
Rejected: a second managed file and settings entry widen the footprint for the same
session-start moment.

## Risks / Trade-offs

- A clone with `core.hooksPath` set still runs no hook until the person acts; now the dry-run,
  the confirmed run and every session start say so.
- The check runs two extra `git` calls per session start in a consumer; they are local reads.
- A future pre-commit release that changes its `# ID:` line would make both readers report a
  missing hook — visible, never silent; the constant is one place per reader, pinned by a test.

## Migration Plan

No migration: the next `init` run in a clone installs the hook, and consumers get the new check
with the release that ships it. Rollback is reverting the PR; an installed hook stays and is
the state the manual row asked for.
