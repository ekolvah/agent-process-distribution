## Why

`principles.md` ships in the plugin and is the canon for every consumer (issue 431), yet three
principles are written for one product or for this repository's gates. Observation on `main`
(`e8e77b6`):

- §III speaks only of a pipeline, its notification and persisted dedupe state.
- §IV names "extraction", "notification delivery" and "summarization", and states its
  enforcement as "CI enforces ruff `BLE001` … blocked by `tests/test_ruff_silence_rules.py`".
  That path does not exist (the test is `tests/agent_process/test_ruff_silence_rules.py`), and
  the ruff selection a consumer gets from install (`distribution` spec, "Init seeds the
  baseline toolchain") adds `C901` and the `PLR` rules, not `BLE` or `TRY400`.
- §VI lists "bad selectors, unresolved macro placeholders" and ends at "a scheduled production
  run".

A consumer without notifications, selectors or that test reads rules that do not apply, or a
gate it does not have.

## What Changes

- `principles.md` §III, §IV and §VI state each rule for any consumer, §III's rationale
  included. Headings, and so the anchors `SKILL.md` links, are unchanged.
- §IV keeps the rule and drops this repository's ruff gate from the canon (design D2).
- Governance: **MINOR** (design D3); no explicit approval is needed in the PR description.

## Capabilities

### New Capabilities

### Modified Capabilities

## Impact

- Edited: `skills/agent-process/principles.md`. No spec delta (`skip_specs`): no requirement
  changes; the text is principle prose (§I documentation exception).
- Added, removed: none. No ADR: the wording decisions and their alternatives are in
  `design.md`.
