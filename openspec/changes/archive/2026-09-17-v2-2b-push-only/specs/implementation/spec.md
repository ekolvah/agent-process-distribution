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
how a `P0`/`P1` thread the push addressed is resolved — `resolve_review_thread` on that
thread from the implementer's own session — and SHALL resolve no other thread: a `P2`/`P3`
finding is answered, and its disposition is the person's. The review check runs on
pushes alone, a resolve has no event of its own, and the required context is the head's
`pull_request` run: the loop SHALL resolve an addressed thread once the Codex review of
the new head is in, re-run that completed run (`gh run rerun`) so it reads the resolve,
and reply on the thread after the resolve. A review fix that changes a spec SHALL go through a change
of its own on the PR branch — a delta under `openspec/changes/<change>/specs/`, validated
and archived by `archive_change` before the push — never through a direct edit of
`openspec/specs/`: the archive is what carries a spec, on the first PR and on every
fix. The tasks after the
archive SHALL leave no tick in the repository — the PR is their record — and a run
interrupted after the archive SHALL resume from `gh pr view <change>`, not from the apply.
The PR body SHALL name the tracking issue as a plain reference, not with a `Closes` keyword:
the branch from `gh issue develop -c` closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` begins with the verdict and branch tasks on an existing tracking issue, asks nothing, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule

#### Scenario: Propose run stopped before its tail
- **WHEN** the apply starts on a change whose `tasks.md` still reads `<N>` or whose tracking issue is not in `Planned`
- **THEN** the gate task prints `propose run not finished` and the run stops before the branch task, asking nothing

#### Scenario: Blocking thread addressed
- **WHEN** a push of the review loop addresses a `P0`/`P1` thread
- **THEN** the Deliver group of `tasks.md` names `resolve_review_thread` for that thread and names no resolve for a `P2`/`P3` thread

#### Scenario: Review fix changes a spec
- **WHEN** a fix in the review loop changes what a spec requires
- **THEN** the Deliver group names a change of its own for it — delta, validation, `archive_change` — and `openspec/specs/` is edited by the archive alone
