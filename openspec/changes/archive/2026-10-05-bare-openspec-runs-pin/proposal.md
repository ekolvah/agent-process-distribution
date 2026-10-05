## Why

The OpenSpec skills and commands that `init` installs (`.claude/skills/openspec-*`,
`.claude/commands/opsx/*`) call bare `openspec`, and nothing puts that command on `PATH`
(#343). Observation, this session, plugin 3.8.1 on Windows + git-bash:
`command -v agent-process` → `…/agent-process/3.8.1/bin/agent-process`,
`command -v openspec` → not found; `/opsx:propose` fails with `openspec: command not
found`. Root cause: upstream generates the bare command and offers no way to change
it, while the process runs OpenSpec only as `npx -y @fission-ai/openspec@1.13.0`. The pin is
also typed by hand in five places (`init.py`, `archive_change.py`, `SKILL.md` twice,
`tests/publisher/openspec_cli.py`), so a bump can miss one.

## What Changes

- The plugin ships `bin/openspec` beside `bin/agent-process`: it runs
  `npx -y @fission-ai/openspec@<pin> "$@"`, so the bare command resolves to the pin wherever the
  plugin is enabled, with nothing installed globally.
- `init.py`'s `OPENSPEC` is the one written pin. `archive_change.py` and the publisher tests take
  it from there; `bin/openspec` is the one copy, and a test fails when it differs or when any
  other file outside `openspec/changes/` writes an OpenSpec version.
- `SKILL.md` prints bare `openspec` (Verify, spec correction) instead of the `npx` form.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the plugin's `bin/` runs bare `openspec` at the pin that `init` installs.

## Impact

- Added: `bin/openspec` (mode 100755).
- Edited: `skills/agent-process/scripts/archive_change.py`, `skills/agent-process/SKILL.md`,
  `tests/publisher/openspec_cli.py`, `tests/publisher/test_init_config.py`,
  `tests/publisher/test_plugin.py`.
- Spec: `openspec/specs/distribution/spec.md` through the delta of this change.
- Removed: none. No ADR: the pin and the `npx` runner are unchanged (ADR 0027, 0033 D5); this
  only adds a launcher for them.
