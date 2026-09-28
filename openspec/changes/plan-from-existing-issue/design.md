## Context

See proposal.md — Why. The `tracking issue <N>` token of Group 0 is the only carrier of the
issue number to `create_tracking_issue` and `start_change` (ADR 0027, `v2-2f-start-change`).
Its existing-issue branch is specified and tested (`planning` / Existing tracking issue);
what is missing is the step that puts the number there.

## Goals / Non-Goals

**Goals:** the planner writes the source issue's number into the token when it writes
`tasks.md`, so the tail takes the existing-issue branch.

**Non-Goals:** no change to either script; no cleanup of the duplicate, already closed by hand (#241).

## Decisions

**D1 — The procedure names the value, not a script guard.** Group 0 of `SKILL.md` says the
token carries the number of the issue the change is planned from, or the placeholder `<N>`
for the tail to replace. The planner writes Group 0 itself, so the number goes in where the
planner already writes the token.

Alternatives:
- A guard in `create_tracking_issue` against a duplicate: the script has no deterministic
  link from a change to its source issue (the title of #199 is not the change name, the
  proposal need not cite it), so any guard is a heuristic that can refuse a genuine new issue.
- An `--issue <N>` flag on the tail: a second carrier beside the token that `start_change`
  would still need in `tasks.md`, and the same planner choice at a later step.
- Rewording the `area required` refusal: the observed run passed `--area` directly (#199),
  so the refusal was never printed; no observation shows it would have helped.

No new script or check, so the bespoke-check decision does not apply.

## Risks / Trade-offs

- [The planner still writes `<N>` for an issue-born change] → the tail creates a duplicate as
  before (#242), visibly: its output names the new issue number, which differs from the source
  issue the planner started from, and the source issue stays out of `Planned`. The rule sits
  in Group 0, the text the planner copies when writing the token.

## Migration Plan

Rollback: revert the PR; the scripts are unchanged, so no state migrates.
