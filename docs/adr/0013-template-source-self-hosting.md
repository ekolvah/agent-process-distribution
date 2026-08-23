---
status: accepted
date: 2026-08-23
decision-makers: [repository maintainers]
---

# ADR 0013: Gate the self-applied root against a working-tree render

## Context and Problem Statement

This repository is both the Copier template source and a consumer of that
template. A root-only edit and a template-only edit can otherwise diverge
silently, leaving either this repository or downstream consumers with stale
process code.

## Decision Drivers

* Detect a stale source or generated payload before it reaches consumers.
* Keep exceptions explicit, narrow, and unable to silently rot.

## Considered Options

* Working-tree render-and-compare gate.
* Generated-root-only or template-only layout.
* `copier recopy --pretend`.
* Snapshot library or auto-rendering fixer.

## Decision Outcome

Chosen option: "Working-tree render-and-compare gate", because it compares the
two real copies without depending on downstream Copier metadata or adding a
third snapshot copy.

The pytest drift gate copies `copier.yml` and `template/` into a git-free
temporary directory, renders it with this checkout's non-volatile answers, and
compares the result with the root. Generated files must match after CRLF/LF
normalisation. The allowlist declares root-only files and files expected to
differ; stale rows fail. Extra files are reported and fail only in declared
strict directories.

The repair direction is always to edit `template/` and re-render the root.

### Consequences

Uncommitted template edits are visible to the gate, so a same-commit template
change and re-render can pass. The gate does not auto-fix drift, compare
downstream consumers, or verify the LF-only pre-push contract after newline
normalisation; `.gitattributes` and its dedicated test retain that safeguard.

## Pros and Cons of the Options

### Working-tree render-and-compare gate

* Good, because it sees uncommitted template edits and stale allowlist rows.
* Bad, because each gate run performs a Copier render.

### Other options

* Bad, because layout-only options lose self-application coverage; `recopy`
  needs consumer metadata; snapshots duplicate the payload; and auto-rendering
  hides rather than reports drift.
