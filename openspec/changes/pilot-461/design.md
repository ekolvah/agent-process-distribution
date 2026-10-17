## Context

See proposal.md — Why. `create_tracking_issue` is the propose tail: it validates
`architect-review.json`, then creates the issue from `proposal.md` (placeholder token) or moves
the existing one to `Planned`. It runs after the review, and nothing ties an `approve` to the
artifacts' current text.

## Standard approach

MADR (<https://adr.github.io/madr/>), which this repository's ADRs use, records "Considered
Options" and links the resources a decision rests on. The plan follows it: the section links the
source, and the `bespoke` class judges it.

The standard for a required-section check, markdownlint MD043
(<https://github.com/DavidAnson/markdownlint/blob/main/doc/md043.md>), compares headings only, in
one file: it cannot express "either file" nor the body form, and markdownlint is not in the
toolchain (`.pre-commit-config.yaml` runs ruff and local hooks). The design departs from it.

## Goals / Non-Goals

**Non-Goals:** checking that a URL resolves or is relevant; gating `start_change` again (it reads a
plan that already passed the tail); an exemption flag for analysis-only issues — they do not run
the propose tail (`grep -i analysis` over `SKILL.md` and `openspec/specs/` finds no such route),
and a change acting on their conclusions passes the gate.

## Decisions

- **The form check lives in `create_tracking_issue`, after the verdict and before both branches.**
  A plan without the section never becomes `Planned`. Alternative: `start_change` — rejected, the
  plan is already presented as ready by then.
- **Form:** the section runs from a `## Standard approach` line to the next `#` or `##` heading;
  it passes when it holds `http://` or `https://`, or `none found:` followed by text on the same
  line. The exit-2 message names both forms and says to review again, since the `approve` it
  follows never judged the section; nothing is created or moved.
- **Content is the `bespoke` class**, whose schema description gains a clause for every plan: a
  missing section is a finding, otherwise whether the source is the standard approach and why the
  design follows or departs from it. So the review, which runs first, catches a missing section in
  its own round, and the script gate is the backstop. No new class: every review file stays valid.
- **Unlike the removed `additions` regex** (ADR 0027), `none found:` is a valid outcome, so no plan
  must cite an unrelated source, and the scope is one section, not every non-test file. ADR 0027
  gets one bullet saying so.

## Risks / Trade-offs

- [In-flight plans without the section stop at the tail after upgrade] → the exit-2 message names
  what to add; rollback is reverting the commit.
