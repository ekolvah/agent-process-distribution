## Why

The `setup` that `init` seeds into `.github/agent-process-quality.json` installs
`pre-commit==4.6.0 pytest==9.0.3` first and the project's `requirements.txt` and
`requirements-dev.txt` after. When a requirements file pins the same tool at another version,
the later `pip install -r` silently replaces the seeded pin: CI runs whichever install came
last, and the seed is dead configuration that drifts unnoticed (tracking issue 470).

**Observed:** `ekolvah/lampa-mediacenter` PR #32 — its `requirements-dev.txt` pins
`pytest==9.1.1`; the review bot flagged the double pin (P3) and the project removed
`pytest==9.0.3` from its `setup` (commit `b8b546b`).

**Reproduction:** `tests/publisher/test_init.py::test_quality_command_marker[fresh]` with the
expected seed of design D1 fails on the current seed, which pins both tools.

**Root cause:** the seed pins the tools itself, so the template, not the project, owns their
versions.

## What Changes

- The seeded `setup` installs `pre-commit` and `pytest` without a version in the same
  `pip install` as each present requirements file: one resolution, so every version the
  requirements pin stays.
- Existing declarations are untouched (`init` never changes one); only fresh seeds change.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: requirement *Init asks for no quality command* — the seeded `setup` leaves
  the tool versions to the project's requirements.

## Impact

- Edited: `skills/agent-process/templates/agent-process-quality.json` (the seed).
- Edited: `tests/publisher/test_init.py` (`_seeded`).
- Edited: `.agent-process/docs/adr/0035-init-seeds-a-baseline-quality-toolchain.md` (D3, D4).
- Edited: `openspec/specs/distribution/spec.md` through the archive of this change.
