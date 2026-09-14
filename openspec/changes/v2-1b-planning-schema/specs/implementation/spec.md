## Purpose
How the process gets correct implementations out of agents, how rework after CI is kept
low, and how an agent turn ends.

## ADDED Requirements

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with the delivery tasks
(tracking issue with priority, `gh issue develop -c`, `set_status "In Progress"`, the
provenance line) and end with `ci_check`, the PR, the `wait_for_pr` loop and one last task,
`finish_change <change>`. After the tracking issue exists no delivery task SHALL prompt the
person. The review loop between the PR and `finish_change` SHALL be bounded: after three
rounds of applying unresolved threads the run leaves the rest to the person with a reply
and ends. The PR body SHALL name the tracking issue as a plain reference, not with a
`Closes` keyword: the branch from `gh issue develop -c` closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `agent-process` schema
- **THEN** its `tasks.md` begins with the tracking-issue tasks and ends with `finish_change <change>`, per the `tasks` rule
