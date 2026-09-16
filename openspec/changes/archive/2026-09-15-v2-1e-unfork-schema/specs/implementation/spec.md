## MODIFIED Requirements

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with the delivery tasks
(the priority asked before the tracking issue is created, `gh issue develop -c`,
`set_status "In Progress"`, the provenance line) and end with `ci_check`,
`archive_change <change>`, the PR and the `wait_for_pr` loop. After the tracking issue
exists no delivery task SHALL prompt the person. The review loop after the PR SHALL be
bounded: after three rounds of applying unresolved threads the run leaves the rest to the
person with a reply and ends. The tasks after the archive SHALL leave no tick in the
repository — the PR is their record — and a run interrupted after the archive SHALL resume
from `gh pr view <change>`, not from the apply. The PR body SHALL name the tracking issue
as a plain reference, not with a `Closes` keyword: the branch from `gh issue develop -c`
closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` begins with the priority and tracking-issue tasks, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule
