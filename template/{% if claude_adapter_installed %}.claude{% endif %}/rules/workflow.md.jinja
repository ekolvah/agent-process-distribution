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

Claude is an available `planner` adapter: `/plan #N` runs the
[planner runbook](../../.agent-process/docs/architecture/agent-process.md#planner-runbook)
and invokes the local `architect-reviewer` subagent.

Claude also carries `discovery` through the `discovery` subagent that the same
`/plan #N` run invokes on a bug issue whose Evidence block is not
yet accepted. There is no separate human entry point: the role is chained
inside the planner run, the way the architect review already is.

Claude also adapts `implementer` and `fixer` through
`/implement #N`, so one agent carries an issue from plan to PR.
The role catalogue selects the default adapter and route for this project.

When creating an issue, ask the user for priority and set the GitHub Project
field with `python .agent-process/scripts/set_issue_priority.py <N> <High|Medium|Low>`.
