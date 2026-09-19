## MODIFIED Requirements

### Requirement: Delivery steps are tasks of every change
The `tasks` rule in `config.yaml` SHALL make every `tasks.md` begin with `start_change
<change>` — the gate (the verdict read and the tracking issue as a Project item in
`Planned`), `gh issue develop -c` on that issue, `set_status "In Progress"` and the
provenance line in one command whose conditions are exit codes — and end with `ci_check`,
`archive_change <change>`, the PR and the `wait_for_pr` loop. No delivery task SHALL
prompt the person or create the issue: the priority was asked by the propose run, which
SHALL write the issue number into Group 0 of `tasks.md` (the placeholder `<N>` replaced).
`start_change` SHALL exit 2 without creating a branch when the verdict does not start with
`approve`, and SHALL print `propose run not finished` and exit 2 when `tasks.md` still
reads `<N>` or the issue is not in `Planned`. The review loop after the PR SHALL be
bounded: after three rounds of applying unresolved threads the run leaves the rest to the
person with a reply and ends. The loop SHALL name how a `P0`/`P1` thread the push addressed
is resolved — `resolve_review_thread --thread --reply-file` on that thread from the
implementer's own session — and SHALL resolve no other thread: a `P2`/`P3` finding is
answered, and its disposition is the person's. The step after `wait_for_pr` is that one
command, and its order is the script's, not the rule's: it SHALL refuse while the head's
`agent-review` run is running (the review of the head is in when the run concluded,
Codex's or the fallback's the run started when none came), resolve the thread, re-run that
run (a resolve has no event of its own, and the required context is the head's
`pull_request` run) and post the reply last. A review fix that changes a spec SHALL go
through a change of its own on the PR branch — a delta under
`openspec/changes/<change>/specs/`, validated and archived by `archive_change` before the
push — never through a direct edit of `openspec/specs/`: the archive is what carries a
spec, on the first PR and on every fix. The tasks after the archive SHALL leave no tick in
the repository — the PR is their record — and a run interrupted after the archive SHALL
resume from `gh pr view <change>`, not from the apply. The PR body SHALL name the tracking
issue as a plain reference, not with a `Closes` keyword: the branch from `gh issue develop
-c` closes the issue on merge.

#### Scenario: Tasks of a new change
- **WHEN** a change is proposed with the `spec-driven` schema
- **THEN** its `tasks.md` begins with `start_change <change>` on an existing tracking issue, asks nothing, and `archive_change <change>` precedes `gh pr create` in it, per the `tasks` rule

#### Scenario: Propose run stopped before its tail
- **WHEN** `start_change` runs on a change whose `tasks.md` still reads `<N>` or whose tracking issue is not in `Planned`
- **THEN** it prints `propose run not finished` and exits 2 before any branch exists, asking nothing

#### Scenario: Verdict is rework
- **WHEN** `start_change` runs while `architect-review.md` does not start its verdict with `approve`
- **THEN** it exits 2 before any branch exists and names the rework

#### Scenario: Blocking thread addressed
- **WHEN** a push of the review loop addresses a `P0`/`P1` thread
- **THEN** the Deliver group of `tasks.md` names `resolve_review_thread --thread --reply-file` for that thread and names no resolve for a `P2`/`P3` thread; the script refuses while the head's `agent-review` run is running, and on a concluded run resolves the thread, re-runs that run and posts the reply, in that order

#### Scenario: Review fix changes a spec
- **WHEN** a fix in the review loop changes what a spec requires
- **THEN** the Deliver group names a change of its own for it — delta, validation, `archive_change` — and `openspec/specs/` is edited by the archive alone
