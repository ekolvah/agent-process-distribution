## Context

`install` (`init.py:711`) parses arguments, checks the selected release, builds `Context`,
previews another release by hand-off, plans the steps, prints them, stops on conflicts or
dry-run, and applies the steps — all in one body inside one `try … except InstallError`.
`PLR0913` counts its seven parameters; the six keyword ones are the host seams the tests
inject through `tests/publisher/init_harness.install`, the only caller besides `main`.

The change has no spec delta (`skip_specs: true`). Observed with `@fission-ai/openspec@1.13.0`:
`validate refactor-init-install --strict` → valid, "skip_specs is set … zero deltas accepted";
`archive refactor-init-install -y` on a scratch copy → "archived as
'2026-09-23-refactor-init-install'", exit 0 — the command `archive_change.py` runs.

## Goals / Non-Goals

**Goals:** `install` passes the four rules at ruff's default limits with no `noqa`, and every
helper it gains passes them too.

**Non-Goals:** fitting `init._checkout` or `init_harness.install` under the limits; changing
any printed line, exit code, or the order of writes.

## Decisions

- **D1 — `Host` dataclass.** `install(argv: list[str], host: Host) -> int`; `Host` holds
  `root, home, platform, runner, which, on_write`. `main` and the harness build it. The
  inputs are the same values regrouped: no project-declared input is replaced and no guard is
  dropped. Alternatives: merging `on_write` into `Context` (needs the parsed arguments before
  it exists); `**kwargs` (hides the seams from type checking); keeping a `PLR0913` `noqa`
  (fails #162's acceptance).
- **D2 — Two helpers.** `install` keeps parsing, the override line, the selected-release
  guard, building `Context`, and the one `except InstallError`; it delegates to:
  - `_run(ctx, args, argv, on_write) -> int` — the body of the current `try` up to the apply
    loop: another release's dry-run hand-off, plan, report, conflict (2), dry-run (0), then
    `_perform`;
  - `_perform(ctx, steps, argv, on_write) -> int` — the apply loop with its hand-off.

  Every `InstallError` raised in them still reaches the one handler in `install`, so the
  `error:` line and exit 1 stay where they are. More helpers (`_context`, `_preview`, `_plan`)
  were rejected: each would have one caller, and the two above already pass the limits
  (reviewer's scratch run, ruff 0.15.12: `_run` 7/4/7, `install` 5/4/4 for
  complexity/returns/branches).

## Risks / Trade-offs

- [A helper reorders output or swallows an error] → caught by the unchanged
  `tests/publisher/test_init.py`, run by `ci_check.py` in the pre-push hook on the push of
  the archive and by CI's quality job on the PR head; it asserts printed lines, exit codes
  and write order (lifecycle, retry, conflicts, footprint, Project phase).
- [A helper crosses a limit, or the removed `noqa` is left in place] → `ruff` (`C901`,
  `PLR09xx`, `RUF100`) in the `lint` step of the same `ci_check.py` runs.

Rollback is a revert of the PR; nothing outside the repository changes.
