## Why

`always-on.md` reaches every session; §I–VII reach a session only through the skill, when it is
invoked. A session that never invokes it (an ad-hoc fix or edit) misses the operative core of
§I, §IV, §V and §VII that issue 429 lists, and the rules of §II, §III and §VI as well.
Observation on `main` (`d4241de`): `always-on.md` cites `§I–§VII`, `§V`, `§IV`, `§I` and `§VII` and states none of them. Each rule must have one
wording: a second copy in `always-on.md` would drift from `principles.md` with nothing to catch
it, and all seven rules belong in one place (the person's decisions on this plan).

## What Changes

- The operative rules of §I–VII move from `principles.md` into a new `## Operative principles`
  of `always-on.md`, as ADR 0043 moved the goal function. Their `principles.md` sections link it
  and keep only detail, procedure and rationale; the skill's `#principles` becomes one line of
  links to it. `principles.md` drops `## Development Workflow`, which restates its Governance
  (design D1, D2).
- Every `§` in `always-on.md` then resolves inside it; goals 1 and 2 keep names and references
  only, and this repository's `CLAUDE.md` drops its §V bullet and its goal-3 sentence (design D3).
- About 250 more tokens in every installed session, the issue's ceiling (design D4).
- The review contract names the trusted `always-on.md` beside `principles.md` as review
  policy, since the rules leave `principles.md`, and its per-principle breach signals
  become short tags that do not restate the rules (design D2).
- Applied after `consumer-neutral-principles` (issue 431, rewrites §III, §IV and §VI),
  `delegate-exploration-reads` (issue 424, modifies the same roles requirement) and
  `review-checks-every-principle` (issue 430, adds the contract requirement modified here) are
  merged: the edits below are written against their text.
- Governance: **MINOR** (the canon's delegation names `always-on.md` for the rules; no rule is
  removed or redefined); no explicit approval is needed in the PR description.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the installed rules file carries the operative principles, and every `§`
  reference in it resolves inside the file.
- `roles`: the skill and `principles.md` link the operative principles instead of restating them.
- `review-and-merge`: the review contract's policy names the trusted `always-on.md`.

## Impact

- Edited: `skills/agent-process/always-on.md`, `skills/agent-process/principles.md`,
  `skills/agent-process/SKILL.md`, `CLAUDE.md`, `.agent-process/REVIEW_CONTRACT.md`,
  `tests/publisher/test_init_config.py`, `tests/publisher/test_plugin.py`,
  `tests/publisher/test_reusable_workflows.py`, and by archive `openspec/specs/distribution/`,
  `roles/` and `review-and-merge/spec.md`.
- Added: `.agent-process/docs/adr/0044-operative-principles-reach-every-session.md`.
- Removed: none. `init.py` copies `always-on.md` whole, so the installer is unchanged.
