## Context

The consumer's policy (#314) has three portable rules: carrier tiers, one home per fact, and
memory versus repository. The plugin already runs the memory checkpoint hook, which enforces
the last rule at write time. What it lacks is the policy text.

## Goals / Non-Goals

**Goal:** the skill carries the portable policy.

**Non-Goals:**
- a language policy or check (proposal § Why);
- "current state, not history" (#284);
- the consumer's project-specific material: its `docs/architecture` tier names, ADR directory
  policy, doc-header and link guards.

## Decisions

### D1 — `## Documentation` in SKILL.md

Placed after `## Claude harness`. The text:

```markdown
## Documentation

Where an agent writes repository knowledge. Each fact has one home; every other mention links
to it and does not restate it.

- `CLAUDE.md`: a thin router loaded every session — what the project is, environment
  pitfalls, pointers; under 200 lines.
- `.claude/rules/<topic>.md`: one operational topic per file. Frontmatter `paths:` loads it
  only for matching files; without `paths:` it costs as much as `CLAUDE.md`.
- Project docs say how the code works and are read on demand; ADRs say why a decision was made.
- Deterministic checks: [Scripts over instructions](principles.md#scripts-over-instructions).
- Auto-memory holds only facts specific to one machine or one person; a fact every session
  needs goes into the repository.
```

The loading claims are the platform facts quoted from https://code.claude.com/docs/en/memory
in `archive/2026-10-03-skill-carries-harness-context/design.md`, plus, observed 2026-10-04:
"Path-scoped rules trigger when Claude uses the Read, Write, or Edit tool on a file matching
the pattern, not on every tool use."

Alternative: a separate `documentation.md` linked from the skill. Rejected: under 1 KB does
not justify a hop the agent may skip. The skill body is the channel that reaches the agent
(#336). The consumer's rationale paragraphs are not ported: token accounting, the
two-graph-layers model, and the history of its own gates.

### D2 — No language check

The issue's ask was a configurable port of `check_language.py`. The design first chose Vale
through a local pre-commit hook. That choice was dropped because the problem the check closed,
Russian documentation being migrated to English, was one-time and has not recurred. If it does
recur, Vale is the standard to start from.

## Risks / Trade-offs

- Nothing catches a consumer drifting into a second language. The person accepted the gap on
  2026-10-04; a recurrence reopens it through D2.

## Migration Plan

The skill reaches consumers on the next release. Rollback removes the section.

## Open Questions

None.
