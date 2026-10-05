# Proposal

## Why

`wait_for_pr` reports `clean` before the checks the base branch requires exist (issue 348).
Observed with plugin 3.8.3 on ekolvah/kinozal_scraper PR 630: CodeQL (the repository's default
setup) attached at once, the `agent-process` and `agent-review` runs about two minutes later,
and `agent-process wait_for_pr 630`, started right after `gh pr create`, printed

```
waiting: a second read of Analyze (actions), Analyze (python), CodeQL on 3879781
clean: 3 checks green, no unresolved threads (https://github.com/ekolvah/kinozal_scraper/pull/630)
```

while neither `agent-process / quality` nor `agent-review / agent-review` was on the head; a
later run reported `agent-process / quality` failed. Root cause: the script guards only the
empty rollup — any non-empty rollup with no `pending` check, read twice on one head, counts as
settled (`wait_for_pr.py` lines 142–158), so a rollup that so far holds only foreign fast
checks settles. A false green ends the delivery loop (§IV). The two-read settling was the
answer to late checks in `v2-2e-wait-for-pr-checks` (PR 147, round 2), which recorded a gap
longer than 30 s as not proved and left the required contexts out because reading them
"needs admin"; that holds for classic protection only — the rulesets the plugin installs are
readable without it (design D1).

## What Changes

- `wait_for_pr` reads, once, the required status checks of the rules on the PR's base branch,
  and treats a head as settled only once every one of them is among its checks; until then it
  prints `waiting: <absent checks> (not reported)` and reads again; a timeout names them
  (exit 3).
- A base branch with no required check prints one `note:` line saying the wait settles on the
  reported checks only, then waits as today.
- `SKILL.md` Delivery and the script's docstring say the same; ADR 0027's "not proved" line
  narrows to the gap left.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: requirement "The implementing run ends only after checks and reviews" —
  settled requires the base branch's required checks on the head, not only a non-empty rollup.

## Impact

- Edited: `skills/agent-process/scripts/wait_for_pr.py`, `tests/publisher/test_pr_delivery.py`,
  `skills/agent-process/SKILL.md` (Delivery sentence),
  `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md` (its
  `wait_for_pr` bullet's claim that required contexts need admin and that runs attach at once,
  and the `wait_for_pr` entry's "Not proved" line, design D3).
- Spec: `openspec/specs/implementation/spec.md` through this change's delta.
- No file added or removed.
