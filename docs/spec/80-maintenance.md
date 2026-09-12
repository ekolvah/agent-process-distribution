# Maintenance

**Question this document answers:** how the process stays small while agents extend it,
and how future support of the process itself is kept low.

Status: draft

## Requirements

- **MAINT-1** (MUST) **Native first.** A process script exists only when it is shown that
  GitHub, `gh`, Claude Code or Codex do not already do the job. The ADR for any core
  addition carries a section "Native alternatives considered".
- **MAINT-2** (MUST) **A script is justified by an observed, repeated failure**, never a
  hypothetical one. A single failure is fixed by a line in the skill; the second
  occurrence earns the script.
- **MAINT-3** (MUST) Core scripts are stack-agnostic: `gh`, `git` and the standard
  library only. Anything stack-specific is the consumer's `AGENTS.md` or `ci_check`.
- **MAINT-4** (MUST) Tests in this repository cover the scripts (unit); consumer
  conformance is the consumer's own `ci_check`. No publisher/consumer test split, no
  rendered-template tests.
- **MAINT-5** (MUST) Versioning: plugin version and git tag `vN`; reusable workflows are
  pinned by tag in consumers; a breaking change is a major tag with a migration note.
- **MAINT-6** (MUST) Every ADR that adds to the core states what would be deleted if the
  addition stopped paying for itself.
- **MAINT-7** (MUST) Size budget: core scripts ≤ 1 000 lines, workflows ≤ 150 lines
  (GOAL-6). Exceeding it is a finding, not a default.
- **MAINT-8** (SHOULD) Deterministic rules live in scripts with exit codes, prohibitions in
  deny-lists or hooks, never in prose the agent has to remember
  (`principles.md`, "scripts over instructions").
- **MAINT-9** (MUST NOT) No self-applied template of this repository; no backward
  compatibility of internal script APIs — only the skill's user-facing commands and the
  reusable workflow inputs are contracts.
