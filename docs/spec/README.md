# System specs

**Question this document answers:** what a system spec is in this repository, how it is
written, and how it relates to issues and ADRs.

| Artifact | Question | Lives in | Lifetime |
| --- | --- | --- | --- |
| **System spec** | how the process is built | `docs/spec/NN-area.md` | living: edited in the same PR as the change |
| **Change spec** | what changes this time | the GitHub issue | until the PR merges |
| **ADR** | why a decision was taken, what it supersedes | [`.agent-process/docs/adr/`](../../.agent-process/docs/adr/) | immutable |

The spec holds requirements only. Rationale, alternatives, traceability to earlier
decisions and open questions belong to the ADR or the issue that introduces or changes
a requirement; the issue names the IDs it implements.

**Target vs. current.** Until v2 lands these specs describe the **target** process;
[`agent-process.md`](../../.agent-process/docs/architecture/agent-process.md) remains the
**current** contract that the gates enforce.

## Format

- `**Question this document answers:** …` header, then `Status: draft | accepted | superseded`.
- `## Requirements` — `- **PREFIX-N** (MUST | MUST NOT | SHOULD) statement`. One prefix
  per file; a dropped requirement keeps its number (struck through), never reused.
- File names `NN-slug.md`, step of 10, so a new area slots in without renames.

A draft may be merged; the PR that implements its requirements flips it to `accepted`.
A superseded spec keeps its file with a pointer to the successor until nothing links to it.

## Index

| Spec | Area |
| --- | --- |
| [00-goals.md](00-goals.md) | scenario, goal function, success criteria |
| [10-distribution.md](10-distribution.md) | install and update channels, consumer footprint |
| [20-roles.md](20-roles.md) | roles, two agents, skills as the single carrier |
| [30-planning.md](30-planning.md) | issue form, planner skill, architect review, human approval |
| [40-implementation.md](40-implementation.md) | RED-first, `ci_check`, end of the agent turn |
| [50-review-and-merge.md](50-review-and-merge.md) | advisory review, ruleset, conversation resolution |
| [60-state.md](60-state.md) | GitHub Project status and priority |
| [70-telemetry.md](70-telemetry.md) | token-efficiency measurement |
| [80-maintenance.md](80-maintenance.md) | native-first, when a script is justified, versioning |
