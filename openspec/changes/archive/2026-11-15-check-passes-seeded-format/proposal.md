## Why

In a freshly adopted consumer the first run fails `agent-process / quality`: the `ruff-format`
hook that init seeds rewrites the managed `.claude/agent-process-check.py` (tracking issue 521).
A consumer reformatting it is pointless, since the next init restores the managed copy.

Reproduction: `ruff format --isolated --diff skills/agent-process/templates/skill_check.py`
(ruff 0.15.12, the seeded pin; `--isolated` is a consumer with no ruff config) prints five
hunks, among them `return MARKER, "cannot check: ..."` and the `subprocess.run(...)` call
re-wrapped.

Root cause: the consumer's formatter formats a file the consumer does not own. The template is
formatted under this repository's `line-length = 100`; a consumer formats it under its own
configuration — ruff's default 88 when it has none.

## What Changes

- `skills/agent-process/templates/skill_check.py` gains `# fmt: off` as its second line, so
  ruff leaves the managed check as shipped under any consumer configuration. Its behaviour does
  not change.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: a new requirement — the seeded `ruff-format` leaves the installed skill check
  unchanged.

## Impact

- Edited: `skills/agent-process/templates/skill_check.py` (one comment line),
  `tests/publisher/test_init_config.py` (one parametrized test),
  `openspec/specs/distribution/spec.md` (via archive).
- No ADR: ADR 0035's toolchain decision stands; this keeps a managed file out of its formatter.
- Consumers: the next init installs the check with the comment; a consumer-side exclusion of
  the file from `ruff-format` becomes unnecessary and may be removed.
