---
status: "accepted"
date: 2026-10-16
decision-makers: ekolvah
---

# The operative principles reach every session

## Context and Problem Statement

ADR 0043 put the goal function into every session through `always-on.md`. Principles §I–VII
did not follow: a session read them only through the skill's one-line `#principles` summary,
and only when the skill was invoked, so an ad-hoc fix or edit worked without the operative rule
of §V (instrument first), §VII (surgical changes), §I (RED first and its narrow exemptions) or
§IV (no fail-open branch). `always-on.md` also cited `§I–§VII`, `§I`, `§IV`, `§V` and `§VII`,
and nothing in a consumer session without the skill resolved them.

## Considered Options

* Move the operative rule of each of §I–VII into a `## Operative principles` section of
  `always-on.md`; `principles.md` and the skill link it
* A second wording of the rules in `always-on.md`, `principles.md` unchanged: two copies drift
  with nothing to catch it
* Generate the section from marked sentences of `principles.md`, or test that they match: a
  script or check where moving the text removes the problem
* Move only §I, §IV, §V and §VII: the rules of §II, §III and §VI would keep a second home
* Import `principles.md` whole: about 3,400 tokens per session (ADR 0043)

## Decision Outcome

Chosen: **move the operative rules into `always-on.md`**. `## Operative principles` sits between
the goal function and the harness and holds one bullet per principle, opening with its `**§N**`;
it is the only wording of these rules and holds no link, so the installed copy reads the same.
Each section of `principles.md` opens with a link to it and keeps only detail, procedure and
rationale; `## Development Workflow`, which restated Governance, is gone, and Governance names
`always-on.md` as the holder of the rules of §I–VII. The skill's `#principles` becomes one line
of links. Goals 1 and 2 keep names and `§` references only, so every `§` in the file resolves
inside it. This repository's `CLAUDE.md` drops its §V bullet and its goal-3 sentence, which the
imported file now states.

The review job follows no link from the contract, so `REVIEW_CONTRACT.md` names the trusted
`always-on.md` beside `principles.md` as review policy, and its per-principle breach signals
become short tags that leave the rule to its one wording.

This is a MINOR amendment: the canon's delegation names `always-on.md` for the rules; no rule
is removed or redefined.

### Consequences

* Good, because a session that never invokes the skill acts on §I–VII, from its first prompt
  and after compaction.
* Good, because each rule has one wording; `principles.md` and `SKILL.md` shrink.
* Bad, because every installed session pays more: `always-on.md` grows from 2,656 to 3,607 bytes
  (`wc -c`), 2,635 to 3,523 characters, about 240 tokens at 3.7 characters per token, near the
  250-token ceiling; a later rule edit that grows the section is cut elsewhere.
* Bad, because a section of `principles.md` no longer reads standalone; a reader follows one link.

### Confirmation

`tests/publisher/test_init_config.py::test_rules_carry_the_always_on_file`,
`tests/publisher/test_plugin.py::test_skill_carries_principles_core_and_harness_tactics` and
`tests/publisher/test_reusable_workflows.py::test_review_contract_labels_each_principle`.

### Deletion condition

Move the section back into the skill once Claude Code loads a plugin's instructions into every
session natively.
