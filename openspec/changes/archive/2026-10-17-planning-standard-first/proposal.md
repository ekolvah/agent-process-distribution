## Why

Planning reads documentation only to check a design that already exists. Nothing makes the
planner ask, before designing, how the vendor recommends using an external tool or what the
industry-standard approach to the problem is, and nothing stops a plan that never asked.

Observed in the analysis of the cheap `jev` model (tracking issue 451 records it): the
model's facts were verified from its docs, but the first prefilter measurement was designed
ad hoc. The vendor's usage recommendations ("best when each question asks one specific,
well-scoped thing") were applied only in a second run, and the standard approach, model
cascades, was mentioned in the conclusions with no source.

## Standard approach

Design-document processes keep a required section for external experience and let "none" be
an answer: the Rust RFC template's `Prior art` ("If there is no prior art, that is fine",
<https://raw.githubusercontent.com/rust-lang/rfcs/master/0000-template.md>) and the KEP
template's `Alternatives`
(<https://raw.githubusercontent.com/kubernetes/enhancements/master/keps/NNNN-kep-template/README.md>).
They gate in two layers: a script checks presence and form (Kubernetes `kepval` fails a KEP
without its PRR approval file, <https://github.com/kubernetes/enhancements/pull/2327>), and a
named reviewer judges the content (PRR approval, blocking since 1.21,
<https://www.kubernetes.dev/resources/keps/1194/>). Claude Code's guidance draws the same
line: CLAUDE.md instructions are advisory, a hook script is the deterministic gate, and a
verification subagent is the second opinion (<https://code.claude.com/docs/en/best-practices>).
This change follows both layers; `design.md` Context names where it departs.

## What Changes

- The skill's `## Proposal` reading bullet defines prior art and where it is recorded: a
  `## Standard approach` section of `design.md` or `proposal.md` with its source, or
  `none found:` with what was searched (design decision 1).
- `create_tracking_issue` exits 2 and creates nothing when neither file carries that section
  with a URL or `none found:` and text (decision 3).
- The architect review's `bespoke` class judges the section's content: whether the source is
  the standard approach and why the design follows or departs from it (decision 2).
- ADR 0027 gains one bullet recording the gate and why it differs from the removed `additions`
  check (decision 4).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `planning`: "The planner reads before writing" defines prior art and its section; "Human
  approval is the gate" names the section check beside `openspec validate`; "Architect
  review is the last step of the propose run" adds the section check to the propose tail and
  widens the `bespoke` finding to the section's content.

## Impact

- Edited: `skills/agent-process/SKILL.md`, `skills/agent-process/architect-review.schema.json`,
  `skills/agent-process/scripts/create_tracking_issue.py`,
  `tests/publisher/test_planning_workflow.py`, `tests/publisher/test_start_change.py`,
  `tests/publisher/delivery_fakes.py`,
  `.agent-process/docs/adr/0027-v2-standards-replace-the-bespoke-control-plane.md`.
- Specs (through this change's delta): `planning`.
- Consumers: after the plugin update, every propose run needs the `## Standard approach`
  section before its tail creates or moves the issue. `start_change` does not check it, so a
  change approved before the update still applies. The review file's shape is unchanged.
