# State tracking

**Question this document answers:** where the process records which task is in which
stage, and what moves it.

Status: draft

## Requirements

- **STAT-1** (MUST) The GitHub Project's built-in `Status` field is the lifecycle field.
  No process-owned state file exists.
- **STAT-2** (MUST) Transitions use the Project's built-in automations where they exist:
  item added → Todo, issue closed or PR merged → Done.
- **STAT-3** (MUST) One script, `set_status`, moves an issue to In progress when
  implementation starts. It resolves field and option IDs by **name** at run time from
  the Project number held in a repository variable; nothing is generated per project.
- **STAT-4** (MUST) Priority is a Project field set when the issue is created; the skill
  asks the person for it.
- **STAT-5** (MUST) The stage of a delivery is readable from GitHub alone: Project
  status, linked branch, PR checks, review threads. An agent or a person resuming work
  reads those, not a local ledger.
- **STAT-6** (MUST NOT) No custom status values beyond the Project's own; the process
  does not create the Project (`init` links to an existing one); no local attempt ledger
  for delivery.
