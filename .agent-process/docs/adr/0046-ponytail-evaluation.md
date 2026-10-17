---
status: "rejected"
date: 2026-10-17
decision-makers: ekolvah
---

# Ponytail is not adopted as an optional plugin

## Context and Problem Statement

Ponytail v5.3.2 (tag `v5.3.2`, `16352ac229eb08a9598dcae48fe9f2b342567d86`) is a Claude Code
plugin. Its Node hooks on `SessionStart`, `SubagentStart` and `UserPromptSubmit` inject a
"lazy senior developer" ruleset into every session and subagent. Five skills come with it
(`-review`, `-audit`, `-debt`, `-gain`, `-help`), and a per-turn ledger writes to
`~/.config/ponytail/band/`. The question was whether it changes what the process delivers
when §VII, `## Standard approach` and the review's `bespoke` class already apply.

The comparison table of the archived design
(openspec/changes/archive/2026-10-17-evaluate-ponytail/design.md) finds:
- six overlaps: the minimum-code ladder against §VII and *Scripts over instructions*, the bug-fix rule, `ultra`, `-review`/`-audit` against `/simplify` and the architect review, and the ledger;
- three conflicts: §I, §V and §IV;
- two costs: tokens injected per session, and Node.

## Considered Options

* Adopt as an optional plugin: one optional row in the skill's Install
* Not planned

## Decision Outcome

Chosen: **not planned**. The pre-registered rule required B to pass in each task, and task 1 failed.

**Paper gate.** It passed, and every conflict resolved without editing Ponytail's ruleset:
- §I takes precedence over "leaves one small test";
- §V takes precedence over a `shortcut:` comment that links no issue;
- the silent `ponytail-subagent.js` (§IV) is covered by a transcript check for the ruleset's opening line;
- the ledger closes with `ledger=false`.

**Method.** The pilot compares two arms on two merged tasks:
- arm A is the historical delivery without Ponytail;
- arm B delivers the same task again with `--plugin-dir`, from A's base, into a `pilot-base/<slug>` branch under a temporary ruleset.

The rule: B has no more P0/P1 `agent-review` findings and no more architect-review rounds, green CI, RED first, no fewer tests, and no `shortcut:` without an issue. B must also cost less or change fewer lines.

| Reading | per-task-rates A | B | planning-standard-first A | B |
| --- | --- | --- | --- | --- |
| `cost_usd` | 6.16 | 6.94 | 11.43 | 7.62 |
| `hours` | 1.24 | 0.74 | 1.34 | 0.63 |
| `plan_rounds`, `code_rounds` | 4, 1 | 2, 1 | 4, 1 | 2, 1 |
| `lines`, files | 307, 11 | 355, 10 | 530, 15 | 435, 15 |
| findings P0/P1/P2 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/1 |
| tests added | 1 | 1 | 2 | 3 |
| RED first, `shortcut:` | yes, 0 | yes, 0 | yes, 0 | yes, 0 |
| added dependencies, scripts | 0, 0 | 0, 0 | 0, 0 | 0, 0 |

Task 1's B meets every floor but costs more and changes more lines, with a narrower scope. Task 2's B passes. The person ran task 2 anyway, although the rule made task 1 decide. After the readings, they chose not to install Ponytail and gave no per-task merge verdict.

**Limits:**
- Each cell ran once, so n = 2. The two tasks point in opposite directions, which is consistent with run-to-run variance.
- A ran in interactive sessions with the person's interventions. B ran in headless `claude -p` sessions on build 2.1.296, against A's 2.1.300, with no agent identity.
- B's architect reviewer also ran under Ponytail, so its rounds are a judgement from inside the arm.
- B's CI failed only `agent-process / link` and the `quality` gate behind it. GitHub links a PR to an issue only when the PR targets the default branch, so this is a setup artifact.

**Leak.** The first task-2 B run used A's slug and A's issue text, read A's merged delivery on `origin/main`, and was discarded. The rerun used three guards:
- a neutral slug;
- an appended system prompt that forbids reading anything made after the base;
- `--disallowedTools` on A's PR, A's issue, PR, issue and code search, and `git show` of A's merge commit.

The rerun's transcripts carry no leak.

### Consequences

* Good, because the process takes on no Node runtime, no external plugin with 14 releases in its
  first month to re-pin, and no conflict resolutions to re-check on each release.
* Good, because Ponytail removes none of the process's own mechanisms. Those are scripts, hooks,
  CI gates and branch protection, and a prompt ruleset cannot replace a gate. As an optional
  plugin it also cannot replace the overlapping prose, which a consumer without it still needs.
* Bad, because a possible token saving, as in task 2, stays unmeasured beyond n = 2.

### Confirmation

The skill's `## Install` has no Ponytail row.

## More Information

Reopen the question if either of these holds:
- a Ponytail release lets a consumer delete a script, gate or rule of this process;
- a pilot with repeated runs per cell shows lower cost or fewer changed lines in every task.
