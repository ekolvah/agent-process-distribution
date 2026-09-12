# State tracking

**Question this document answers:** where the process records which task is in which
stage, and what moves it.

Status: draft

## Requirements

- **STAT-1** (MUST) The GitHub Project's built-in `Status` field is the lifecycle field
  (ADR 0024 stands). No process-owned state file exists.
- **STAT-2** (MUST) Transitions use the Project's built-in automations where they exist:
  item added → Todo, issue closed or PR merged → Done.
- **STAT-3** (MUST) One script, `set_status` (~80 lines), moves an issue to In progress
  when implementation starts. It resolves field and option IDs by **name** at run time
  from the Project number held in a repository variable; nothing is generated per project.
- **STAT-4** (MUST) Priority is a Project field set when the issue is created; the skill
  asks the person for it.
- **STAT-5** (MUST) The stage of a delivery is readable from GitHub alone: Project
  status, linked branch, PR checks, review threads. An agent or a person resuming work
  reads those, not a local ledger.

## Rationale

v1 carried `bootstrap_github_project.py` (403 lines) to create or verify a Project and
generate `project_settings.py` with node IDs, plus `set_issue_status.py` and
`set_issue_priority.py` embedding those IDs, plus `state.json` and `delivery_state.py` for
the orchestrator. Resolving by name costs one GraphQL query and removes the generated file
and the bootstrap; dropping the orchestrator removes the ledger. GitHub already holds the
state that matters (STAT-5); a second copy could only drift.

## Non-goals

- Custom status values beyond the Project's own.
- Creating the Project from the process; `init` links to an existing one.
- A local attempt ledger for delivery (the owner's telemetry ledger in `70-telemetry.md`
  is measurement, not process state).

## Open questions

- Whether `init` verifies that the Project has the required `Status` options or only
  records the number; settled when the second project is migrated.

## Traceability

- ADR 0024 (built-in Status is the lifecycle field) — kept.
- `bootstrap_github_project.py`, `project_settings.py`, `set_issue_status.py`,
  `set_issue_priority.py`, `state.example.json`, `delivery_state.py` — replaced by STAT-3.
