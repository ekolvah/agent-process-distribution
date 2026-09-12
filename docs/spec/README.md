# System specs

**Question this document answers:** what a system spec is in this repository, how it is
written, and how it relates to issues and ADRs.

## Three artifacts, three questions

| Artifact | Question | Lives in | Lifetime |
| --- | --- | --- | --- |
| **System spec** | how the process is built | `docs/spec/NN-area.md` | living: edited in the same PR as the change |
| **Change spec** | what changes this time | the GitHub issue (issue form) | until the PR merges |
| **ADR** | why a decision was taken | `docs/adr/` | immutable |

The system spec is the current truth. An ADR is written only when a decision changes; the
spec is updated in that same PR. An issue references the requirement IDs it implements
(`DIST-3`), so a PR can be traced to the requirement it satisfies.

**Target vs. current.** Until v2 lands, these specs describe the **target** process;
[`agent-process.md`](../../.agent-process/docs/architecture/agent-process.md) remains the
**current** contract that the gates enforce. `90-migration-v1-v2.md` tracks the gap.

## Format

Every `NN-slug.md` file — the guard is `tests/publisher/test_spec_structure.py`:

1. `**Question this document answers:** …` header before the first section.
2. `## Requirements` — one list item per requirement:
   `- **PREFIX-N** (MUST|SHOULD) statement`. One prefix per file, unique across files;
   numbers are never reused after a requirement is dropped (strike it, keep the ID).
3. `## Rationale` — why these requirements, including the v1 lesson where one exists.
4. `## Non-goals` — what this area deliberately does not do.
5. `## Open questions` — decisions not yet taken, each with what would settle it.
6. `## Traceability` — ADRs and issues this spec draws from or supersedes.

File names carry a two-digit prefix with a step of 10 so a new area slots in without
renames. A spec stays under 150 lines; when it grows, split by area, never by date.

## Lifecycle

`draft` → `accepted` → `superseded`. The status line sits directly under the header.
A draft may be merged; it becomes accepted when its requirements are implemented and the
implementing PR flips the line. A superseded spec keeps its file with a pointer to the
successor until nothing links to it.

## Index

| Spec | Area |
| --- | --- |
| [00-goals.md](00-goals.md) | scenario, goal function, non-goals, success criteria |
| [10-distribution.md](10-distribution.md) | install and update channels, consumer footprint, consumer extensions |
| [20-roles.md](20-roles.md) | roles, two agents, skills as the single carrier |
| [30-planning.md](30-planning.md) | issue form, planner skill, architect review, human approval |
| [40-implementation.md](40-implementation.md) | RED-first, `ci_check`, end of the agent turn |
| [50-review-and-merge.md](50-review-and-merge.md) | advisory review, ruleset, conversation resolution |
| [60-state.md](60-state.md) | GitHub Project status and priority |
| [70-telemetry.md](70-telemetry.md) | token-efficiency measurement |
| [80-maintenance.md](80-maintenance.md) | native-first, when a script is justified, versioning |
| [90-migration-v1-v2.md](90-migration-v1-v2.md) | v1 → v2 plan; deleted once v2 lands |
