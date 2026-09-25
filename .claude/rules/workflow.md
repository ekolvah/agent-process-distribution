# Claude workflow adapters

**Question this document answers:** Which workflow roles Claude adapts in this
project, without becoming the source of the workflow contract.

The portable planning and delivery procedure is in
[`skills/agent-process/SKILL.md`](../../skills/agent-process/SKILL.md). The enforced
workflow, roles, delivery gates, and provenance are specified in `openspec/specs/`. Do not
duplicate either contract here.

Before invoking a planner or implementer in a newly adopted repository, follow
[Install](../../skills/agent-process/SKILL.md#install).

Claude is an available `planner` adapter: `/opsx:propose` runs the OpenSpec propose
workflow with the project context and skill pointers of `openspec/config.yaml` and invokes the local
`architect-reviewer` subagent, which writes the change's `architect-review.json`
([architect review](../../skills/agent-process/SKILL.md#architect-review)).

Claude also adapts `implementer` and `fixer` through `/opsx:apply <change>`, whose
task list carries the delivery steps
([delivery](../../skills/agent-process/SKILL.md#delivery)),
so one agent carries a change from approved plan to archived PR.

When creating an issue, ask the user for priority and set the GitHub Project
field with `python skills/agent-process/scripts/set_status.py <N> --priority <High|Medium|Low>`
(`Todo` comes from the Project's own workflow). The propose run creates the
tracking issue of a change and leaves it in `Planned`.
