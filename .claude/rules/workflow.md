# Claude workflow adapters

**Question this document answers:** Which workflow roles Claude adapts in this
project, without becoming the source of the workflow contract.

The portable planning and delivery procedure is in
[`skills/agent-process/SKILL.md`](../../skills/agent-process/SKILL.md). The current enforced
workflow, roles, issue contract, delivery gates, and provenance remain in
[`agent-process.md`](../../.agent-process/docs/architecture/agent-process.md). Do not duplicate
either contract here.

Before invoking a planner or implementer in a newly adopted repository, follow
[the installation guide](../../.agent-process/docs/architecture/agent-process-installation.md).
The generated `.agent-process/scripts/project_settings.py` must be committed before the
process can move issue statuses.

Claude is an available `planner` adapter: `/opsx:propose` runs the OpenSpec propose
workflow with the project context and skill pointers of `openspec/config.yaml` and invokes the local
`architect-reviewer` subagent, which writes the change's `architect-review.md`
([planning](../../.agent-process/docs/architecture/agent-process.md#planning)).

Claude also adapts `implementer` and `fixer` through `/opsx:apply <change>`, whose
task list carries the delivery steps
([deterministic delivery flow](../../.agent-process/docs/architecture/agent-process.md#deterministic-delivery-flow)),
so one agent carries a change from approved plan to archived PR.

When creating an issue, ask the user for priority and set the GitHub Project
field with `python skills/agent-process/scripts/set_status.py <N> --priority <High|Medium|Low>`
(`Todo` comes from the Project's own workflow). The propose run creates the
tracking issue of a change and leaves it in `Planned`.
