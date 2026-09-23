## Why

`install` in `skills/agent-process/scripts/init.py` is the one function whose complexity
baseline (#161, ADR 0028) is tracked for removal (#162). While its `# noqa` stays, the four
rules no longer bound the function the installer grows in (complexity 13 → 14 in #160).
Observed on `main` at `e73fa5b`: `python -m ruff check --ignore-noqa --select
C901,PLR0911,PLR0912,PLR0913 skills/agent-process/scripts/init.py` (ruff 0.15.12) reports for
`install` complexity 14 > 10, 8 returns > 6, 14 branches > 12, and 7 arguments > 5.

## What Changes

- `install` takes `argv` and one `Host` value (root, home, platform, runner, which, on_write)
  instead of six keyword arguments, and delegates to two private helpers (`_run`, `_perform`), so it passes
  `C901`, `PLR0911`, `PLR0912`, `PLR0913` without suppression; its `# noqa` is removed.
- `main` and the test harness `tests/publisher/init_harness.install` build a `Host`. The
  harness keeps its own signature and baseline (out of scope, #162); only its call and the
  reason text of its `noqa` change.
- Installer output, exit codes, and write order are unchanged; `tests/publisher/test_init.py`
  is not edited.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — a behaviour-preserving refactor; the change sets `skip_specs: true`.

## Impact

- Edited: `skills/agent-process/scripts/init.py` (`Host`, `install`, `_run`, `_perform`,
  `main`), `tests/publisher/init_harness.py` (the `init.install` call and its `noqa` reason).
- Not edited: `tests/publisher/test_init.py`; `.agent-process/docs/adr/0028-…` — its list is
  the baseline *at adoption* and stays true as a record; `init._checkout` keeps its baseline.
- No new dependency, file, or check.
