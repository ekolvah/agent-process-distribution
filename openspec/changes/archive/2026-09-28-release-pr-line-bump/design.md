## Context

`release_pr.py` decides the release exemption of the `link` and `agent-review` gates
(ADR 0031). Its version-only test replaces the old version everywhere in a file, while
release-please rewrites only the annotated line and the JSON version fields
(proposal, run 36472852057).

## Goals / Non-Goals

**Goals:** a real release PR passes when a versioned file keeps an unrelated literal of the old
version; every non-version edit still disqualifies the PR.

**Non-Goals:** reproducing release-please's per-format updaters; changing the release set, the
reads or the gates.

## Decisions

**D1 — Compare line by line.** `_beyond_the_version` splits base and head with
`splitlines(keepends=True)`; the counts must match, and each head line must equal its base line
or that line with every `old → new` bump applied. A line ending change counts as a changed line.
No new script or check: the existing check's rule is corrected.

What stops proving: that every place of the old version in a versioned file was bumped, since
an unchanged line now passes. The catcher that is reached is
`tests/publisher/test_plugin.py::test_version_drift`, run by `ci_check.py` in the `check` job
on the release PR's head (ADR 0031 D3): it asserts that the plugin, the marketplace and the
annotated `VERSION` line of `init.py` hold the manifest's version.

Alternatives:
- *Accept only lines annotated `x-release-please-version` and JSON `version` fields* —
  mirrors release-please's updaters (generic annotations, blocks, JSON paths, TOML, YAML) in
  bespoke code that drifts with them; the line rule needs no knowledge of formats.
- *Drop the `3.0.2` literal from the `init.py` comment* — unblocks PR 258 only; the next literal
  of an old version blocks the next release again.

## Risks / Trade-offs

- A PR may now keep an old version on a line or bump it on a line release-please would not
  touch; either way no line changes other than by the version, which is what the exemption
  needs to hold.
- A PR that reorders lines fails, because lines are compared by position; release-please does
  not reorder.

## Migration Plan

None for consumers: the gates read the script from the trusted process source. After the merge
release-please rebuilds PR 258 and its gates re-run. Rollback: revert the PR.
