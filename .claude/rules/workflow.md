# Claude workflow adapters

**Question this document answers:** Which workflow roles Claude adapts in this
project, without becoming the source of the workflow contract.

The canonical development workflow, roles, issue contract, delivery gates, and
agent provenance are in
[`.agent-process/docs/architecture/agent-process.md`](../../.agent-process/docs/architecture/agent-process.md).
Do not duplicate them here.

Before invoking a planner or implementer in a newly adopted repository, follow
[the installation guide](../../.agent-process/docs/architecture/agent-process-installation.md).
The generated `.agent-process/scripts/project_settings.py` must be committed before the
process can move issue statuses.

Claude is an available `planner` adapter: `/opsx:propose` runs the OpenSpec propose
workflow with the project rules of `openspec/config.yaml` and invokes the local
`architect-reviewer` subagent for the `architect-review` artifact
([planning](../../.agent-process/docs/architecture/agent-process.md#planning)).

Claude also adapts `implementer` and `fixer` through `/opsx:apply <change>`, whose
task list carries the delivery steps
([deterministic delivery flow](../../.agent-process/docs/architecture/agent-process.md#deterministic-delivery-flow)),
so one agent carries a change from approved plan to archived PR.

When creating an issue, ask the user for priority and set the GitHub Project
field with `python .agent-process/scripts/set_status.py <N> "Todo" --priority <High|Medium|Low>`.
