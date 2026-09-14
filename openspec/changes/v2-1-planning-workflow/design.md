## Context

Umbrella design: `v2-0-decision-record/design.md`. This change replaces the planner and
implementer procedures with OpenSpec skills plus thin GitHub glue. Current state that shapes
the work (verified on OpenSpec 1.13.0 and `gh` on this machine, tracking issue #111):

- The change directory exists since the OpenSpec adoption (#105) and validates against the
  baseline (#109); it was written before the schema fork and lacks `architect-review.md`.
- The v1 planner entry points are `commands/plan.md`, `commands/implement.md`,
  `agents/discovery.md`, `.agents/skills/{plan-issue,implement-issue}/`,
  `.agents/orchestration/change-classes.yaml`, `validate_issue_sections.py` (tested by
  `test_validate_issue_status.py`; `test_adr_records.py` imports its `find_gaps`),
  `capture_external_fixture.py` and `check_fixture_ratchet.py` (no CI step or test consumes
  them). All are root-only after `v2-0b` (#119).
- `check_red.py` takes pytest paths and spawns pytest (`[--full] path…`).
- A Codex review is requested by comment (`request_codex_review.py --request <PR>`), is not
  visible in `reviewRequests`, and the v1 `agent-review` required check waits for it
  (bounded) before it concludes; it must be re-requested after every push, as the check
  binds to the head. Observed on the `v2-0b` PR (#120).
- The branch is named after the change, not `issue-*`: `open_pr.py` refuses it and the v1
  Stop hook and `verify_pr_link` are inert on it. `gh issue develop -c N --name <change>`
  still links branch and issue.
- A stale `openspec/changes/archive/.openspec-archive.lock` was observed on the ADR 0027 PR (#118, Windows);
  its cause is not yet known.

## Goals / Non-Goals

**Goals:** one PR that moves planning and implementation onto the OpenSpec skills, ends
through its own `tasks.md` (`wait_for_pr` → `finish_change`), and records what it observed.

**Non-Goals:** review and state rework (`v2-4`), the orchestrator and `roles.yaml` (`v2-5`),
`init` (`v2-2`), a Codex end-to-end apply run (deferred to the apply of `v2-2`), a
machine-produced review-round counter (prose cap until a run overruns it).

## Decisions

- **The change directory is the plan; the issue is the tracker.** `openspec/changes/<name>/`
  holds proposal, deltas, design, architect review, tasks. The GitHub issue holds title,
  change name and priority and is the Project item. Alternative: issue body as the plan (v1)
  — no validator, no archive, no living spec.
- **Project specifics are configuration, not a second skill.** `config.yaml` `rules:` per
  artifact are injected into `openspec instructions`; the forked schema inserts
  `architect-review` between `design` and `tasks`. Alternative: bespoke `plan-issue` skill —
  re-implements the propose loop once, worse.
- **Approval = the person runs `/opsx:apply <change>`.** OpenSpec's planning boundary stops
  `propose` before code; nothing implements until that command. No approval state file.
- **Delivery steps are tasks, not a wrapper skill.** The `tasks` rule puts the GitHub steps
  (issue, branch, status … `ci_check`, PR, `wait_for_pr` loop, `finish_change`) into every
  `tasks.md`, so the unmodified `openspec-apply-change` — the command the generated propose
  prompt hands off to — runs them. Alternative: an `implement-change` wrapper — a second entry
  point the OpenSpec prompts do not know, so it gets bypassed. A re-run on an open PR
  continues at the first unchecked task.
- **`finish_change` closes the loop itself.** The apply skill marks a task after running it,
  and `openspec archive` moves `tasks.md`; so the last task is one script that marks its own
  box first, then archives, commits, pushes, re-requests the Codex review when
  `request_codex_review.py` is present (says so when not) and waits — nothing is left to edit
  after the archive commit.
- **Lock: root cause before handling.** One observation settles it — `openspec archive -y` on
  a scratch change in a temporary `openspec init` directory, then inspect — whether 1.13.0
  leaves the lock after a successful archive on Windows (upstream bug → issue link and a
  deletion condition in ADR 0027) or only after an abort. Either way `finish_change` exits 2
  before archiving when a lock exists and removes the one a successful archive leaves.
- **`wait_for_pr` sees the Codex review through the check, not the API.** It polls
  `gh pr view --json statusCheckRollup,headRefOid` until every check on the head concluded —
  a running check (`agent-review` waiting for the requested review included) is "pending" —
  then reads GraphQL `reviewThreads(isResolved:false)`. Exit 0: nothing unresolved; 1: failed
  checks or unresolved threads printed; 3: `--timeout` (default 30 min) elapsed. Stays until
  `v2-4` reworks review.
- **Review budget: three rounds.** The `tasks` rule caps the apply-threads loop at three
  rounds; the fourth leaves the remaining threads to the person with a reply (#106 ran 16
  rounds). Prose, not a counter — a deterministic guard only after an observed overrun.
- **`set_status.py` duplicates the `gh project` helpers on purpose.** Project = the issue's
  existing project item, else the one Project linked to the repository (several → exit 2
  naming them); field and option by name; `item-add` when absent; unknown option → exit 2
  listing the options, nothing changed. Importing `set_issue_status.py`/`set_issue_priority.py`
  would couple the survivor to scripts that die in `v2-4`; the docstring says so.
- **`check_red --report <junit.xml>` reuses the runner's verdict.** It parses an existing
  report and spawns nothing; `AGENTS.md` declares the runner command and the report path. The
  v1 CLI stays for the RED step of this very change.
- **Delivery of this PR.** Branch `v2-1-planning-workflow` via `gh issue develop -c 111`;
  status through the v1 `set_issue_status.py` (present until `v2-4`); PR with
  `gh pr create --body-file`; `request_codex_review.py --request <PR>` after every push;
  `wait_for_pr` is the only end guard in Claude too — the ADR 0021 → ADR 0027 supersession,
  observed and recorded.
- **`principles.md` §V changes in the same PR.** The `planning` delta forbids the core to
  prescribe evidence capture; canon wins on conflict, so the paragraph becomes "reproduction
  is a step of planning; the `proposal` rule says what it records" and its links to the
  removed anchors are retargeted.

## Risks / Trade-offs

- [Forked schema drifts from upstream `spec-driven`] → `openspec schema validate agent-process`
  in `test_openspec_valid.py` catches it.
- [Codex has no Stop hook] → `wait_for_pr` is the only end guard; the Codex end-to-end run
  is observed at the apply of `v2-2`, named as a deferral in the PR body.
- [A planner drops a delivery task] → the architect review and the PR reviewer read
  `tasks.md` against the `tasks` rule template.
- [`roles.yaml` keeps dangling `contract:` anchors] → its consumer is the orchestrator and its
  tests, not the files; no test resolves the anchors; gone in `v2-5`.
- [`openspec instructions proposal --json` grows if principles §I–VII are appended to
  `context`] → measure both sizes before deciding; the numbers go to ADR 0027.
- [Private-repo auto-close on merge not observable here] → this repository is public;
  deferred to the consumer migration (#117).

## Migration Plan

One PR; the change archives as its last commit through `finish_change`; the person merges.
Rollback: revert the PR — the v1 entry points return; the forked schema and
`architect-review.md` disappear with it.
