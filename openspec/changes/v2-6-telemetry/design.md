## Context

Umbrella design: `v2-0-decision-record/design.md`.

## Decisions

- **One local collector for both agents**; project identity rides OTLP resource
  attributes, task and attempt identity are created by the launcher before the agent starts.
- **Per-PR metrics only**; raw token sums are never compared between versions.
- **Owner-side module**, not part of the plugin, skills or workflows.
