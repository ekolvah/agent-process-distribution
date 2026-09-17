## MODIFIED Requirements

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with the delivery tasks
(the gate — the verdict read and the tracking issue as a Project item in `Planned` —,
`gh issue develop -c` on that issue, `set_status "In Progress"`, the provenance line) and
end with `ci_check`, `archive_change <change>`, the PR and the `wait_for_pr` loop. No
delivery task SHALL prompt the person or create the issue: the priority was asked by the
propose run, which SHALL write the issue number into Group 0 of `tasks.md` (the placeholder
`<N>` replaced), and a change whose `tasks.md` still reads `<N>` or whose issue is not in
`Planned` SHALL stop the apply at the gate with a printed `propose run not finished` line.
The review loop after the PR SHALL be bounded: after three rounds of applying unresolved
threads the run leaves the rest to the person with a reply and ends. The loop SHALL name
how a BLOCKING thread the push addressed is resolved — `resolve_review_thread` on that
thread from the implementer's own session, before the `agent-review` run on that head
reaches its last step — and SHALL resolve no other thread: a finding that is not
BLOCKING is answered, and its disposition is the person's. The tasks after the archive
SHALL leave no tick in the repository — the PR is their record — and a run interrupted after
the archive SHALL resume from `gh pr view <change>`, not from the apply. The PR body SHALL
name the tracking issue as a plain reference, not with a `Closes` keyword: the branch from
`gh issue develop -c` closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` begins with the verdict and branch tasks on an existing tracking issue, asks nothing, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule

#### Scenario: Propose run stopped before its tail
- **WHEN** the apply starts on a change whose `tasks.md` still reads `<N>` or whose tracking issue is not in `Planned`
- **THEN** the gate task prints `propose run not finished` and the run stops before the branch task, asking nothing

#### Scenario: Blocking thread addressed
- **WHEN** a push of the review loop addresses a BLOCKING thread
- **THEN** the Deliver group of `tasks.md` names `resolve_review_thread` for that thread after the re-request of the review, and names no resolve for a thread that is not BLOCKING
