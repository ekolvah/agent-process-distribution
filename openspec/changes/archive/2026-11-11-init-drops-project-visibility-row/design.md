## Context

See proposal.md — Why.

## Standard approach

none found: a removal of an unneeded check; no external tool or API is added.

## Decisions

**D1 — Delete the row and its read, not make it dismissable.** `rows` drops the
`project-visibility` branch, `QUERY` drops `public`, and `_project_state` returns
`(missing, areas)`. Alternatives: an opt-out flag or a persisted "private on purpose" marker
— both add state for a target nothing in the process needs (§VII).

**D2 — The fake follows the query.** `init_harness.Project` drops `public` and its answer drops
the key, so a code path that still read `project["public"]` would raise `Unreadable` in the
tests instead of passing silently.

Dropped proof: `init` no longer reports a private linked Project; nothing downstream needs it
(proposal Why), so there is no catcher to name.

## Risks / Trade-offs

None.

## Migration Plan

None: a consumer's next `init` run omits the row. Rollback is a revert of the PR.
