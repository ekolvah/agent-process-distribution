## Context

Root cause and reproduction are in the proposal. `check_secrets` builds one argv from all
targets; `_run` fails the check on the first non-zero exit.

## Decisions

### Batch by measured command-line length, on every platform
`check_secrets` packs targets in order into batches while `subprocess.list2cmdline` of the
batch's `_secrets_cmd` stays at most `_CMDLINE_LIMIT = 32000` — under the 32767 of
`CreateProcess`, with margin for the terminating null. `list2cmdline` is what
`subprocess` passes to `CreateProcess` on Windows, so the measure is the real string. Each batch
goes through `_run`: the first batch with a finding exits 1. The same batching runs on Linux,
so CI exercises the path Windows depends on.

Alternatives:
- `detect-secrets scan` (walks git-tracked files itself, no argv): it writes a baseline and
  does not fail on a finding (`python -m detect_secrets scan <dir>` exited 0 where
  `python -X utf8 -m detect_secrets.pre_commit_hook <file with AKIA…>` exited 1); the hook is
  the gating entry point.
- Calling `detect_secrets.pre_commit_hook.main(targets)` in-process: no argv limit, but it drops
  `-X utf8`, which the check needs for Windows/Linux parity (comment on `_secrets_cmd`).
- Batch by a fixed file count: path lengths vary, so a count guarantees nothing.

### Fail fast on the first failing batch
Reusing `_run` keeps one exit path. A finding in a later batch surfaces on the next run after
the first is fixed; the check never passes while any batch fails.

## Risks / Trade-offs

- A single path longer than the limit cannot fit any batch: the helper puts it in a batch of
  its own and the OS error surfaces as today, not a silent skip.
- More processes: two on today's tree; negligible against the scan itself.

Rollback: revert the commit; no state or config changes.
