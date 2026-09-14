## Context

Umbrella design: `v2-0-decision-record/design.md`.

## Decisions

- **Scenario title is the coverage key.** `tasks.md` maps `Scenario: <title>` → test node id
  or `n/a: <reason>`; `check_coverage` parses the change's `specs/**/spec.md` and `tasks.md` from
  `openspec/changes/<change>/` or, on the archive commit, `openspec/changes/archive/*-<change>/`,
  plus the JUnit report of the CI run (`openspec show` does not see archived changes). Alternative: markers in
  test docstrings — a second place to keep in sync.
- **Requirement-level coverage is a repository test**, not a consumer check: it iterates
  `openspec/specs/` and greps this repository's tests for each requirement title.
- **Enforcement is a required check**, so an uncovered scenario blocks the merge button
  without a reviewer.

## Open Questions

- JUnit vs pytest-only report: the stack-agnostic input is the JUnit XML most runners emit.
