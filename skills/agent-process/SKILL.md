---
name: agent-process
description: Plan, implement, review, and deliver the shared GitHub agent development process.
---

# Agent process

Use this procedure for both Claude Code and Codex. Repository-specific facts remain in
`openspec/config.yaml`; this skill owns the portable planning and delivery procedure. Run
repository operations from the consumer repository root and resolve helper scripts relative
to this skill directory.

## Proposal

- Read the code and prior art before writing. Ask the person when a scope decision is theirs.
- For a bug, record the reproduction and root cause under **Why** before any design.
- **Impact** lists every file added, edited, and removed; keep doc-only work separate.
- When a design rests on platform behaviour, verify it before the proposal and record the
  observation, not the inference: cite the reference page and sentence, or a run id or exact
  command output. Point to an observation already on record instead of repeating it.

## Specifications

- Specs contain requirements and scenarios only. Put rationale, alternatives, non-goals,
  and open questions in `design.md` or an ADR.
- Keep requirement titles short and stable. A rename is a RENAMED delta plus the matching
  test rename in one change.
- Each scenario names an observable outcome using the stock OpenSpec structural headings
  and SHALL/MUST keywords in English.

## Design

- Record decisions, alternatives, risks, and the migration and rollback boundary.
- A design that replaces a project-declared input with one the caller supplies, or drops a
  guard, lists beside the decision the new input's failure modes, what stops proving, and for
  each lost proof the catcher that is actually reached: which script, which run, on which head,
  not a role or the platform in general.

## Tasks

Write these groups in order and end `tasks.md` with `## Scenario → test map`, mapping every
delta scenario to a named test or `n/a: <reason>`.

1. Group 0 — Delivery start: one task runs `python
   skills/agent-process/scripts/start_change.py <change> --planner <Claude|Codex>
   --implementer <Claude|Codex>`. Its text carries `tracking issue <N>`; the propose tail
   replaces the placeholder. On `rework`, apply the findings and run the review again. A
   `propose run not finished` result stops before a branch is created.
2. Group 1 — RED first: write the tests in the scenario-to-test map and run `python
   skills/agent-process/scripts/check_red.py <node ids>`. It owns the pytest runner and its
   report path; there is no `--test` runner argument. Commit RED before implementation. When
   the map names no test for docs-only, `skip_specs`, or a rename, record
   `no RED: <reason>` as the task.
3. Implementation groups: one task per scenario, design decision, or review finding, each
   with its verification command. End each coherent group with a commit.
4. Verify: run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and the
   repository's complete quality command.
5. Deliver using the procedure below. The person merges.

## Architect review

After `tasks.md`, review proposal, specifications, design, and tasks against principles
§I–VII. Claude invokes `architect-reviewer`; Codex performs a stated self-review. Write
`architect-review.md` with `## Verdict`, `## Findings`, and `## Scenario coverage`.

A simpler design, a missing scenario mapping, a Group 1 omission without `no RED`, a platform
fact asserted, not observed, a replaced input or dropped guard without the Design lists, or a
catcher the review cannot trace to a reached delivery step is a finding. Findings point at
artifacts instead of restating them. On `rework`, answer every finding and review again. The
propose run ends on `approve`: if the change has no issue, ask once for priority and run
`python skills/agent-process/scripts/create_tracking_issue.py <change> --priority
<High|Medium|Low>`; otherwise run it without priority. The issue must be `Planned` before the
plan is ready.

## Delivery

Start from a clean worktree. Run `python skills/agent-process/scripts/archive_change.py
<change>` before `gh pr create --title "<change>" --body-file <report>`. The report names the
tracking issue as a plain reference, never `Closes`, and carries the scenario-to-test map and
deferrals. The archive is the head the PR opens on.

After creating the PR and after every corrective push, run
`python .agent-process/scripts/request_codex_review.py --request <PR>`. The `agent-review`
check waits for Codex's current-head review and runs the Claude fallback only when no valid
Codex evidence arrives. Then run `python skills/agent-process/scripts/wait_for_pr.py <PR>`;
it waits until two reads 30 seconds apart agree that all checks on one head concluded, then
reads unresolved threads on that head.

Apply findings and repeat at most three rounds. After a push, re-request and run
`wait_for_pr.py` again. A P0/P1 thread the push addressed may be resolved only after the
settled review, with `resolve_review_thread.py --thread <id> --reply-file <path>`; the script
refuses a current-head thread, re-runs the required check, and replies last. A P2/P3 thread is
answered, never resolved by the process. A spec correction uses and archives its own delta,
never a direct edit of `openspec/specs/`. A changed design decision amends the archived
`design.md` and scenario map in the same push. A finding on script behavior must be closed by its class:
test the violated invariant and relevant inputs, including what each switch takes away; test
the class, not the reviewer's example.

Run the repository review gate on the settled current head. Stop only at `ready-for-human`
or the documented three-round escalation. Tasks after archive leave no tick in the
repository because a pushed tick would move the reviewed head. If interrupted after archive,
resume from `gh pr view <change>`, not OpenSpec apply.
