## Context

Every adopter's PR is reviewed under this repository's contract and `principles.md` (the
trusted checkout). A review costs $0.10–0.13 in 5–9 turns (runs 38692248603, 38690472058).

## Decisions

**One breach signal per principle, inside the existing `P0`/`P1` class.** The contract
already blocks on a convention violation; it gains the path of `principles.md` in its policy
source and, in that class, what a breach of each of §I–VI looks like in a diff. The signal is
enough to label and name the section; the full text is read only to settle a borderline case.
- Alternative: name the file only. Rejected by the observation in proposal.md: the reviewer
  followed none of `CLAUDE.md`'s links to it, and nothing in a diff tells it when to look.
- Alternative: read `principles.md` in full every run — about 3,400 tokens on every later turn,
  roughly a tenth of a review; the signals cost under 150.
- Alternative: a separate severity bullet — a second scale beside the convention class.

No ADR: this is the contract's existing severity policy made explicit; ADR 0016's §VII
narrowing stays. Rollback is reverting the contract lines.

## Risks / Trade-offs

- [More blocking findings, some wrong] → each names its section; the fixer answers with a
  rationale, which the contract's no-re-raise rule respects.
- [The signals drift from `principles.md`] → the contract defers to the full text.
