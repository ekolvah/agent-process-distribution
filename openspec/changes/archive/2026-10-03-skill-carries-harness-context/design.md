## Context

What a consumer agent loads today (map: https://claude.ai/artifact/TMEQqGPmL9QdKCL1iVzJ4V):

- **At startup:** its own `CLAUDE.md`, `.claude/rules/` without `paths:`, and the first part
  of `MEMORY.md`. It also gets skill and agent descriptions, but only the descriptions.
- **On invocation:** the `agent-process` skill body loads when the `opsx` workflow points
  at it.
- **Read in full:** `principles.md`, but only by `architect-reviewer`.

Platform facts, cited from https://code.claude.com/docs/en/memory:

- "Rules without `paths` frontmatter are loaded at launch with the same priority as
  `.claude/CLAUDE.md`."
- "target under 200 lines per CLAUDE.md file."
- The `AGENTS.md` sentences are quoted in the proposal's Why.

The plugins-reference sentence about skills is quoted there too. Task 3.3 observes the
skill-body channel live.

## Goals / Non-Goals

**Goals:**
- The working agent of a consumer sees the principles and the harness tactics through the
  skill.
- A consumer can delete its `mindset.md` copy.
- One instruction channel: Claude Code, both here and in consumers.

**Non-Goals:**
- Ad-hoc sessions that never invoke the skill (see Deferred).
- Any change to how the review job reads its policy.
- Rewriting `principles.md`.

## Decisions

### D1 — A principles core at the top of SKILL.md, not the full text

`## Principles` gives:
- the three goals in order;
- one line per §I–VII, each linking its heading in `principles.md`;
- one line that says the full text decides on conflict.

That is about 1 KB on each invocation; the full text costs about 13 KB.

Alternatives:
- Goal function plus one line saying that `principles.md` binds. This is the cheapest form
  (about 0.4 KB) and the only one that cannot drift. Rejected: it gives the working agent no
  principle content unless the agent opens 13 KB. `config.yaml`'s context already gives this
  repository the same kind of pointer, and the gap exists anyway (#315). The seven lines
  are what lets an agent recognise "this is a §V moment" without reading the full text.
- Load all of `principles.md` on every invocation: 13 KB each time, most of it not used
  at a given step.
- A `SessionStart` hook that adds `additionalContext`: a bespoke channel, paid in every
  session even when no process step runs.
- A plugin rule: not supported.

The core lines summarise `principles.md` but do not replace it: its Governance section
already says it wins.

### D2 — The harness tactics: the agreed list, in this repository's wording

`## Claude harness` carries:
- narrow reads, following the navigation hooks without working around them;
- a subagent only for independent work, or for research that needs more than three round
  trips;
- concise by default;
- one foreground wait with a raised `timeout`, never a `sleep` or re-read loop;
- after a compaction between RED and GREEN, recover from the branch, the RED commit and one
  `gh issue view <N>`.

Rejected:
- Asking the person for `/compact` after RED, the consumer's form. The person rejected it:
  recovery from recorded state needs no person and no timing.
- The issue's `TodoWrite` tactic. The tool is not in the current harness tool list.
- "Edit with `Edit`/`Write`, not a heredoc". No cost difference was observed: the
  arguments of either one stay in context.

### D3 — mindset.md is deleted

After D1 and D2, `.claude/rules/mindset.md` would keep only two pointers:
- to SKILL.md `#principles` and `#claude-harness`;
- to `testing.md`.

Both go into the `CLAUDE.md` of D4, which is always-load anyway. That leaves one file fewer
at launch. Nothing reads `mindset.md`'s text: `test_memory_checkpoint.py:59` uses the path
only as a fixture string.

### D4 — AGENTS.md becomes CLAUDE.md

`git mv` keeps the content and the history. The only addition is the two pointers from D3. `.claude/rules/` would also work. `CLAUDE.md`
is chosen because it is Claude Code's documented project file, and the review contract needs
a single entry that links it.

The contract's policy source and the prompt's untrusted-data line name `CLAUDE.md` and
`.claude/rules/`. The review mechanism does not change. Every consumer review today already
runs in a worktree that has the consumer's `CLAUDE.md`, so the move adds no new kind of
exposure. The prompt's untrusted-data line keeps covering it.

### D5 — No new script

The new checks are text assertions in the existing publisher tests. They follow the same
pattern as `test_shared_skill_owns_the_procedure_and_scripts`. No standard checker reads a
skill's prose.

### Deferred — a CLAUDE.md marker block in consumers

An `init`-managed block in a consumer's `CLAUDE.md` would reach ad-hoc sessions that never
invoke the skill. Take it only after an observed failure: an ad-hoc consumer session that
breaks a principle the skill carries.

## Risks / Trade-offs

- **The core can drift from `principles.md`.** The test derives the § anchors from
  `principles.md`, so a renamed or added principle fails the test. Drift in wording has no
  run that catches it. Its only resolver is the `principles.md` Governance line, which the
  core repeats: on conflict, `principles.md` decides.
- **The skill grows by about 2 KB per invocation.** In return, every consumer session loses
  an always-load file.
- **Migration and rollback.** Consumers get the change with the next release. Rolling back
  means reverting the PR. A consumer keeps its `mindset.md` until it has seen the release.
