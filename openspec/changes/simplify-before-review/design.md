## Context

See proposal.md (Why) for the three observed runs and the platform facts. The propose run
ends with the architect review that `## Architect review` of `skills/agent-process/SKILL.md`
specifies. The apply run executes the `tasks.md` that `## Tasks` shapes. Both sections reach
consumers through the plugin, so a sentence there is the whole mechanism.

## Goals / Non-Goals

**Goals:**

- Each step is one clause of `SKILL.md`, asserted by a test.

**Non-Goals:**

- No skip of the pass by size or by kind of change. All three observed changes were medium
  to large, and on plans the pass found duplication in prose.
- No change to the `architect-reviewer`, its schema, the CI review, or
  `.claude/rules/workflow.md`, which links the `## Architect review` section and does not restate it.

## Decisions

### D1. The bundled `/simplify`, not a check of our own

The standard for the job is Claude Code's bundled `/simplify`. Every consumer has it, and its
four angles (reuse, simplification, efficiency, altitude) found the duplication in all three
runs.

Alternatives:

- **Reuse and altitude classes in `architect-review.schema.json`.** The reviewer reports
  findings and does not apply them, and the new classes would be prompt text of our own
  covering what a standard skill already covers.
- **A project skill named `simplify`.** The skills reference says Claude Code's commit
  instructions then run it "right before each commit". That would run it on the plan commit,
  the RED commit and every group commit.
- **A hook.** A hook cannot invoke a skill. It could only block the turn and ask the agent
  to run one, which is a bespoke enforcer for a sentence the agent already follows.

### D2. The plan pass runs once, before the first review

In both plan runs, the edits of `/simplify` introduced defects that only the re-review
caught: a silent 0 or 1 in place of a missing value. Placed before the first review, the
review checks those edits in its own round, instead of `approve → simplify → rework →
approve`. It runs once per propose run: on `rework` the findings are the reviewer's. The
existing first sentence of `## Architect review` takes the clause, so one sentence carries
the order.

The plan's explanation states what `/simplify` changed. That is where a pass that did not
run shows up to the person, since the plan pass has no task to tick.

### D3. The code pass opens Verify

Verify (`## Tasks` item 4) is fixed text that every `tasks.md` copies, so the pass does not
depend on a planner writing a group for it. `openspec validate` and the quality `test` that
follow in the same item check its edits, and the PR opens on the simplified head. This saves
the extra reviewed head of the observed run.

It takes no argument: its default diff, `@{upstream}...HEAD`, is the branch's commits,
because `start_change` sets `origin/<change>` as the upstream and nothing is pushed before the
archive (proposal, Platform facts). That diff includes the approved plan commit. A path
target that leaves the plan out was rejected: `/simplify` was observed on a path only for new
files, not on a tracked file the branch modified, where it may review the whole file. An edit
of the plan at this step is reviewed by the CI review of the PR.

## Risks / Trade-offs

- [The before-review order is unobserved] → The architect review is the catcher of the
  defect class that the pass introduced, and it caught each instance in both observed runs.
  If a first run under the new order still needs a round for a defect from `/simplify`, that
  run is the evidence for a follow-up.
- [`/simplify` unavailable to a consumer] (the reference names `disableBundledSkills` as
  turning bundled skills off) → The pass cannot report edits. The plan explanation, or the
  Verify tick, then says that it did not run. Neither is checked by a script: this is an
  accepted gap.
- [Cost] → Two passes per change (proposal, Impact).

## Migration Plan

Consumers receive the two clauses with the next plugin release. Rollback reverts them and
their tests. No ADR: the archived `design.md` records the decision.
