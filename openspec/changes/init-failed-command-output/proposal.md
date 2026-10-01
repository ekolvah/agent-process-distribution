## Why

When a command `init` runs fails, the operator sees that it failed but not always why (§IV).
While diagnosing release PR #277, `git push` was rejected by the consumer's pre-push hook. stderr
held only `error: failed to push some refs to '…'`. The cause was pre-commit's own report
(`CalledProcessError … git checkout v3.2.3 … pathspec did not match`), which went to stdout, and
the `InstallError` did not show it (recorded in #279).

**Root cause:** `Context.call` in `skills/agent-process/scripts/init.py` builds the diagnostic
from the first non-empty captured stream only (`next(s for s in (stderr, stdout) if s)`), so
whenever stderr is non-empty, stdout is dropped.

**Reproduction:** a `Context` whose runner returns exit 1 with stdout `cause` and stderr
`failed to push` raises `InstallError` without `cause` in its message. This becomes the RED test.

## What Changes

- A failed command's `InstallError` names every non-empty captured stream, stderr first and
  then stdout. An uncaptured (`None`) stream still yields `output not captured` when neither
  stream was captured, and captured empty output still yields `exited <code>:` with no text. The two
  texts are joined by a newline; each is already multi-line output, printed as-is after
  `error: `.
- Out of scope: `templates/skill_check.py` also reports only stderr for its failed `git` and
  `claude` reads. That is a different diagnostic (a session-start marker, not `init`), and no
  loss has been observed there.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: new *Init names a failed command's output*.

## Impact

- Edited: `skills/agent-process/scripts/init.py` (`Context.call`).
- Edited tests: `tests/publisher/test_init.py` (a both-streams case beside
  `test_failure_keeps_absent_streams_visible`).
- Added / removed: none. No ADR and no doc change: the fix is local to one diagnostic, and no
  document describes its format.
