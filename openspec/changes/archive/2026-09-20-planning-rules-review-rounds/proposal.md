## Why

Issue 146. PR 145 (`v2-2d-check-red-test`) took nine review rounds and PR 147
(`v2-2e-wait-for-pr-checks`) three, on diffs of one script, one rule and docs. The rounds
come from three root causes of the plan and the fixer, not from twelve bugs (the analysis
of 2026-09-19 on the two PRs is in the issue and its comment; the observations below are
what the archived changes and the PR threads show):

1. **A replaced input had no list of failure modes, or a wrong catcher.** PR 145 replaced
   a project-declared runner with a caller-supplied string; design.md D1 called the swap
   mechanical and named neither what the new input can do wrong (rounds 1–3) nor what the
   script stops proving once the runner owns the selection (rounds 5–6). PR 147 *had* the
   section ("What the script stops proving") and named who catches each dropped guard —
   "the next `wait_for_pr` of the loop", branch protection — and both catchers were wrong:
   a clean verdict ends the loop, so no next read exists (round 2, P1); protection catches
   required contexts only (an optional late check is a silent green). Round 3 was the same
   gap once more. The architect review approved both designs without tracing the catcher.
2. **The archived artifacts drifted after a design change at review.** Round 3 of PR 145
   deleted the selection and two tests; the archived `tasks.md` scenario map still named
   them (round 4, a P1 of its own). PR 147 amended `design.md`, `proposal.md`, `tasks.md`
   and ADR 0027 ad hoc again. The archive-before-PR order ("the reviewed head is the
   archived one", `v2-1d`) means a decision changed at review has to reach the archived
   `design.md` and the map by the same push, and no rule says so.
3. **The fixer closed each finding by its example, not by its class.** From round 3 of
   PR 145 the gate rests on one invariant — a verdict exists only when pytest ran to the
   end for every node id — written down only at round 8. Each fix was assembled from the
   reviewer's example: `-x` → a count guard (5); a broad node id → `--maxfail=0` (7);
   `--stepwise` → `-p no:cacheprovider` (8); round 9 is a regression of 8 plus the most
   standard completion signal, pytest's exit code, that no round checked. Derived from the
   invariant once, the class closed in one round (`v2-2d-check-red-own-runner`, design.md,
   the round-9 amendment). A reviewer looks for the next counterexample by role; a fix by
   example guarantees the next round.

The rules the propose run and the apply load are the `rules:` of `openspec/config.yaml`
(`v2-1e`, `v2-2b-resolve-thread-rule`: a rule outside `config.yaml` is lost at a
compaction). None of the three says what the three causes need. This change rests on no
platform behaviour.

## What Changes

- `openspec/config.yaml`, a new `design` rule: a change that replaces a project-declared
  input with one the caller supplies (or drops a guard) lists, beside the decision, the
  failure modes of the new input (when one is replaced), what the component stops
  proving, and for each dropped proof the delivery-flow step that catches it — which
  script, which run, on which head — not a role or the platform in general.
- `openspec/config.yaml`, `rules.tasks`, Architect review entry: a replaced input without
  that list, and a catcher the review cannot trace to a step the flow reaches in the
  described case, are findings.
- `openspec/config.yaml`, `rules.tasks`, Deliver group: a review fix that changes a design
  decision amends the archived `design.md` beside that decision and the scenario → test
  map of the archived `tasks.md` in the same push (the archive-before-PR order stays:
  design.md D2 weighs "archive after the review" and rejects it).
- `openspec/config.yaml`, `rules.tasks`, Deliver group — the fixer's contract: a review
  finding on what a script does is closed by its class: the invariant it violates, the
  other inputs that violate it from the tool's own documentation, what each added switch
  takes away, a RED test of the class, not the reviewer's example. The three-round limit
  stays as written.
- `tests/publisher/test_planning_workflow.py`: four tests assert the rule text, one per
  scenario. `.agent-process/docs/architecture/agent-process.md` (Planning; the `fixer` row
  of the roles table) and ADR 0027 (one entry) follow. `agents/architect-reviewer.md` is
  not edited: it reads its contract from the Architect review entry (its step 1).

## Capabilities

### New Capabilities

none

### Modified Capabilities

- `planning`: a design that replaces an input or drops a guard lists failure modes, lost
  proofs and a traceable catcher; the architect review finds a missing list or an
  untraceable catcher.
- `implementation`: the review loop of `Delivery steps are tasks of every change` carries
  the archived-artifact amendment and the fix-by-class contract.

## Impact

Edited: `openspec/config.yaml`, `tests/publisher/test_planning_workflow.py`,
`openspec/specs/planning/spec.md` and `openspec/specs/implementation/spec.md` (through the
archive), `.agent-process/docs/architecture/agent-process.md`,
`.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`. Added:
nothing. Removed: nothing. One PR; the tracking issue is 146.
