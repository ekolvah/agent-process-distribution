## Context

`SKILL.md:31` says "Read the code and prior art before writing", which is read as the
repository's own code. The OpenSpec propose instruction this repository ships also points the
reading at the project: "inspect relevant implementation, nearby tests, configuration, and
documentation outside `openspec/`" (`.claude/skills/openspec-propose/SKILL.md:110`). The
`bespoke` class asks for "the standard for its job" only for "each script or check the plan
adds". `create_tracking_issue` (the propose tail) validates the review and its verdict before
it creates or moves the issue; nothing reads `proposal.md` or `design.md` for content.

The standard approach and its sources are in the proposal's `## Standard approach`: a
required prior-art section, a script for presence and form, a reviewer for content. This
change departs from that pattern in two ways:
- The section is not in the OpenSpec templates; the skill asks for it and the script requires
  it, since the templates are the unmodified `spec-driven`.
- The script runs after the reviewer, in the existing propose tail, whereas `kepval` runs
  before PRR. A plan without the section therefore reaches the reviewer, whose `bespoke`
  class is asked about the section, and the script is the backstop for an approve that missed
  it.

The planning requirement "Human approval is the gate" says the only automated check on a plan
is `openspec validate --strict`; the delta names this form check beside it.

## Goals / Non-Goals

**Goals:** What Changes.

**Non-Goals:** a script that judges whether a source is the standard; a gate for analysis
tasks outside `/opsx:propose` (the person chose this over issue 451's "Applies to
analysis-only issues too": the skill rule reaches an analysis that loads the skill, and a
change acting on its conclusions passes this gate); changing the OpenSpec templates.

## Decisions

### 1. The skill's reading bullet defines prior art and its section

`SKILL.md:31` becomes:

> - Read the code and prior art before writing: the usage guidance of each external tool,
>   model or API the design is built around or that is new to the repository, and the
>   standard approach to the problem. Record them under `## Standard approach` in `design.md`
>   or `proposal.md` with each source's URL, or `none found:` with what was searched. Ask the
>   person when a scope decision is theirs.

The tool clause names only tools the design is built around or that are new to the
repository; otherwise a plan using `gh`, `git` or `pytest` in passing would cite their docs.
`none found:` carries what was searched so that the reviewer can judge it.

**Alternative:** extend the platform-behaviour bullet and the `platform` class. Rejected:
`platform` checks facts the design rests on; the standard approach decides which design to
choose.

### 2. `bespoke` judges the section's content

The class description becomes:

> The `## Standard approach` section: whether its source is the standard approach to the
> problem or its `none found` convincing, and why the design follows or departs from it;
> then each script or check the plan adds and its design.md decision: the problem it closes
> and why its job's standard does not fit; a missing or unconvincing decision is a finding.

**Alternative:** a ninth class `standard`. Rejected: three files repeat the class list (the
schema's `required`, `_CLASSES` in `test_planning_workflow.py` and in `delivery_fakes.py`), and
an `architect-review.json` written before the change would fail validation at `start_change`.

### 3. The propose tail checks the section

`create_tracking_issue` gains a check after the verdict and before either branch creates or
moves anything: `proposal.md` or `design.md` of the change has a `## Standard approach`
heading whose text up to the next `##` heading contains an `http(s)://` URL or `none found:`
followed by text. Otherwise it prints that the section is missing or empty, says to add it
and review again, and exits 2.

- **Problem it closes:** the `jev` analysis observation (tracking issue 451): the skill
  sentence alone was read as the repository's code. The gate catches the plan that reaches
  the tail without the section, whether the reviewer missed it or approved it anyway.
- **Standard for its job and why it does not fit:** markdownlint's `MD043` "is triggered when
  the headings in a file do not match the array of headings passed to the rule"
  (<https://github.com/DavidAnson/markdownlint/blob/main/doc/md043.md>): heading sequence, not
  the text under a heading, and a Node dependency. `openspec validate --strict` (1.13.0)
  passed this change before it had any `## Standard approach`. A custom OpenSpec schema adds no
  content rule: `ArtifactSchema` in `@fission-ai/openspec@1.13.0`
  `dist/core/artifact-graph/types.js:24-31` has only `id`, `generates`, `description`,
  `template`, `instruction` and `requires`, and it would break "the OpenSpec schema is the
  unmodified `spec-driven`". `kepval` is the pattern, not a reusable tool. The check is
  one function in the existing tail.
- **Why it does not repeat `additions`:** that regex asked the reviewer for a reference to an
  issue that does not exist before approve, so it was filled with `#1`. Here the planner
  writes the section before the review and the source exists before the plan. The script
  checks form only; relevance is the class's (decision 2).
- **Placement:** in `create_tracking_issue`, not in `start_change`'s `verdict()`, so a change
  approved before the plugin update still starts.

**Alternatives:**
- A field in `architect-review.json`. Rejected: the reviewer would fill it without web access,
  the `additions` failure.
- A Stop hook. Rejected: it fires on every turn and does not know which change is planned.

### 4. ADR 0027 records it

One bullet after the `additions` removal entry: the rule, the tail check and the class
widening, one sentence each, citing the jev observation without an issue number and why the
check differs from `additions`. Deletion condition: OpenSpec validates required design
sections, so a standard check replaces the function.

## Risks / Trade-offs

- [The planner adds the section after an `approve`, without a new review] → the person's
  approval of the plan is the catcher reached; the exit message says to review again.
- [`none found:` becomes boilerplate] → the `bespoke` class rejects an unconvincing one, and
  the searches it names make that visible.
- [An analysis-only task outside `/opsx:propose`] → not gated; a change that acts on its
  conclusions passes this gate.
