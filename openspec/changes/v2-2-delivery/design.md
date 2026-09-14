## Context

Umbrella design: `v2-0-decision-record/design.md`. This change replaces the Copier mirror
with native delivery channels.

## Decisions

- **Plugin root is the only path.** Hooks, agents and rules resolve from
  `${CLAUDE_PLUGIN_ROOT}`; nothing is copied into the consumer except the footprint.
- **Codex reads the same skill directories** linked from a checkout of this repository;
  `git pull` is the update.
- **The reusable workflow checks out this repository at the pinned tag** to run process
  scripts, so consumers never hold process code.
- **Per-consumer values live in repository variables and `AGENTS.md`**, never in a
  templated file — that is what makes update a replacement.
- **`init` is idempotent on the footprint** and appends to an existing `AGENTS.md`.

## Risks / Trade-offs

- Consumers need Node for `openspec` (`npx`); documented in `init`.
- Codex has no plugin mechanism; the checkout link is a manual one-time step per machine.
