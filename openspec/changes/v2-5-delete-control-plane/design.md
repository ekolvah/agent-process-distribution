## Context

Umbrella design: `v2-0-decision-record/design.md`. Deletion only; every behaviour the
deleted code carried is either a human decision, a GitHub feature, or already delivered by
v2-1 … v2-4.

## Decisions

- **No deprecation period.** Consumers are on v1 tags until they bump; the major tag carries
  the migration note (`Versioning by tag`).
- **Budgets go with the orchestrator.** A looping agent is visible on the PR; a counter hid
  the loop instead of showing it.
