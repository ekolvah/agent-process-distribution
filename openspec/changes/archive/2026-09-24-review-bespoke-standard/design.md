## Context

`start_change.verdict` validates `architect-review.json` against the schema with
`jsonschema`. It runs in `create_tracking_issue`, before an issue exists, and in
`start_change`, before a branch exists. An invalid file exits 2 and names each error
(`test_review_not_valid`). The schema already applies an `if verdict = approve` branch: every
class must be `ok`.

## Goals / Non-Goals

**Goals:**
- An `approve` whose added script, check or non-test file has no observed problem cannot be written.
- The same holds when it names no established standard for the job.

**Non-Goals:**
- Proving the reference is the right problem, or that the standard truly does not fit. That
  stays the `bespoke` class's judgement and the person's solution review.
- Proving the list names every addition. A cross-check against the diff would be a new
  script, and no review has been observed to omit one.
- Issues 113 and 169.

## Decisions

**D1. A top-level `additions` list, beside `scenario_coverage`.** It is required, and it may
be empty. Each item has `path`, `problem`, `standard` and `why_not`, all non-empty strings,
with no other keys. The scope is scripts, checks and non-test files: a test proves a
scenario and has no job of its own.
Alternatives:
- Fields inside `classes.bespoke`. `$defs.class` has `additionalProperties: false`, so this
  needs a second class definition.
- A ninth class. It is free text again.

**D2. The format is enforced under `approve` only.** The schema's `then` branch adds two
checks:
- `problem` must match `^(#[0-9]+|https://github\.com/[^/\s]+/[^/\s]+/(issues|pull|actions/runs)/[0-9]+)$`;
- `standard` must not match `^\s*([Nn][Oo][Nn][Ee]|[Nn]/?[Aa]|-)\s*$`, so any spelling of "none", "n/a" or a dash is rejected.

Under `rework` the reviewer records the gap as found, for example `problem: "none"`, and
writes the `bespoke` finding. A plan therefore gets `approve` only once a reference and a
standard exist.

Observed with jsonschema 4.26.0 on a prototype of this schema:

| Case | Result |
|---|---|
| `"#113"` | valid |
| `"https://github.com/o/r/actions/runs/123"` | valid |
| `"none"` | `'none' does not match '^(#[0-9]+\|…'` |
| `"ADR 0027"` | `'ADR 0027' does not match …` |
| `standard` set to `"none"`, `"None"`, `"N/A"`, `"NA"`, `"-"` or `" n/a "` | `'<value>' should not be valid under {'pattern': …}` |
| `standard: "pytest-bdd"` | valid |
| a `rework` with `problem: "none"` | valid |
| the list absent | `'additions' is a required property` |

**D3. The `bespoke` class judges the list.** Its description becomes: "The list names
every script, check or non-test file of the proposal's Impact and the design. For each
entry, the problem is one the addition closes, and the standard is the one for its job and
does not fit."
- The schema carries the format. The class carries the judgement: whether the list is
  complete, and whether each entry is true.
- So `additions: []` beside a new script in Impact is a `bespoke` finding, not a pass.

**D4. Not edited:**
- `SKILL.md`. Its architect review step already says the file must be valid against the
  schema.
- "Native first" in `maintenance`. Issue 169 decides it.

Standard for this job: JSON Schema, the review's existing validator. Nothing bespoke is added.

## Risks / Trade-offs

- [The reviewer omits an addition from the list] → the schema cannot see the Impact. The
  `bespoke` class checks the list against Impact and the design (D3), and the solution
  review catches the rest. A diff cross-check waits for an observed omission.
- [A real but unrelated reference] → the `bespoke` judgement and the solution review catch it.
- [Every fixture of a valid review needs `additions: []`] → there are two fixtures, both edited
  in RED.

## Migration Plan

It applies to the next propose run once merged. Archived reviews are never validated again.
Rollback: revert the schema and the spec sentence.
