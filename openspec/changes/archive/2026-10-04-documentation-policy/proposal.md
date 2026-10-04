## Why

The consumer `ekolvah/kinozal_scraper` keeps its own policy for agent-written knowledge in
`docs/architecture/information-architecture.md`: which Claude Code carrier holds what, one home
per fact, and memory versus repository (#314). Nothing in it is specific to that product, so
every consumer has to work it out again. The plugin's skill is the only channel that reaches a
consumer's agent (the #336 proposal records the plugin reference sentence).

The issue also asks for a configurable language check to replace the consumer's
`scripts/check_language.py`. The person decided against it on 2026-10-04: the check served a
one-time migration of Russian documentation to English, and no recurrence has been observed
since. A check with no observed problem is support cost with no return, so it is not carried
and the consumer deletes its copy without a replacement.

## What Changes

- `skills/agent-process/SKILL.md` gains a `## Documentation` section, the portable policy:
  - the Claude Code carrier tiers: `CLAUDE.md`, `.claude/rules/` with and without `paths:`,
    project docs and ADRs, code and scripts, auto-memory;
  - one home per fact, other mentions link;
  - auto-memory holds only machine- or person-specific facts.
- Not carried: the language policy and its check (see Why); "current state, not history"
  (#284).
- Consumer follow-up, tracked in ekolvah/kinozal_scraper#615 (sub-issue of epic #614):
  `kinozal_scraper` deletes `scripts/check_language.py` and its `ci_check.py` entry, its
  language section, and, after the release, the portable parts of
  `information-architecture.md`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `roles`: a new requirement makes the skill carry the documentation policy.

## Impact

- Edited:
  - `skills/agent-process/SKILL.md`
  - `tests/publisher/test_plugin.py`
  - `openspec/specs/roles/spec.md` (through the archive)
- Added, removed: none. No ADR: the change adds skill text and no mechanism.
- Consumers: the skill reaches them on the next release.
