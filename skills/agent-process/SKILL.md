---
name: agent-process
description: Plan, implement, review, and install the shared GitHub agent development process.
---

# Agent process

Use this procedure for both Claude Code and Codex. Repository-specific facts remain in
`openspec/config.yaml`; this skill owns the portable planning and delivery procedure.
Resolve every script path relative to this skill directory, even when the skill is linked.

## Proposal

- Read code and prior art before writing. Ask the person when a scope decision is theirs.
- For a bug, record the reproduction and root cause under **Why** before any design.
- **Impact** lists every file added, edited, and removed; keep doc-only work separate.
- When a design rests on platform behaviour, verify it before the proposal and record the
  observation, not the inference: cite the reference page and sentence, or a run id or
  command output. Point to an observation already on record instead of repeating it.

## Specs

- Specs contain requirements and scenarios only. Put rationale, alternatives, non-goals,
  and open questions in `design.md` or an ADR.
- Keep requirement titles short and stable. A rename is a RENAMED delta and matching test
  rename in one change.
- Each scenario names an observable outcome using the stock OpenSpec structural headings
  and SHALL/MUST keywords in English.

## Design

- Record decisions, alternatives, risks, and the migration/rollback boundary.
- A design that replaces a project-declared input or drops a guard lists beside the
  decision: the new input's failure modes, what the component stops proving, and for each
  lost proof the catcher that is actually reached — which script, which run, on which head,
  not a role or the platform in general.

## Tasks

Every change uses these groups, in order.

1. Delivery start: one task runs `python <skill>/scripts/start_change.py <change>
   --planner <Claude|Codex> --implementer <Claude|Codex>`. Its text carries
   `tracking issue <N>`; the propose tail replaces the placeholder. On `rework`, apply the findings and
   review again. A `propose run not finished` result stops before a branch is created.
2. RED first: write the tests in the scenario-to-test map and run `python
   <skill>/scripts/check_red.py <node ids>`. It owns the pytest runner and report path.
   Commit RED before implementation. If the map names no test for docs-only, `skip_specs`,
   or a rename-only expectation, record `no RED: <reason>` as the task; this is the
   Principle I exemption.
3. Implementation: one task per scenario, design decision, or review finding, each with a
   verification command. End each coherent group with a commit.
4. Verify: run `npx -y @fission-ai/openspec@1.13.0 validate --strict --all` and the
   repository's declared complete quality command.
5. Deliver: start with a clean worktree; run `python <skill>/scripts/archive_change.py
   <change>` before `gh pr create --title "<change>" --body-file <report>`. The report names
   the tracking issue as a plain reference and carries the scenario-to-test map and accepted
   trust gaps. Then run `python <skill>/scripts/wait_for_pr.py <PR>` until every check on one
   settled head concludes and inspect every unresolved thread. The automatic Codex review is
   person-configured during install; never request Codex by a process-owned PR comment.
6. Fix/answer at most three rounds. After a push run `wait_for_pr.py` again. A P0/P1 thread
   addressed by a pushed correction may be resolved with `resolve_review_thread.py`; answer
   P2/P3 without resolving it. A spec correction uses and archives its own delta —
   never a direct edit of `openspec/specs/`. A changed design decision amends the archived `design.md`
   and scenario map in the same push. A script finding is closed by its class:
   test the violated invariant and relevant inputs, not the reviewer's example. This is
   "closed by its class" evidence, including what each switch takes away.
7. Before handoff, inspect `gh pr diff <PR> --name-only`, every current-head
   `.github/workflows/**` diff, and visible advisory review state. The person merges.

Tasks after archive leave no tick in the repository: a pushed tick would move the reviewed
head. If interrupted after archive, resume from `gh pr view <change>`, not OpenSpec apply.
End `tasks.md` with `## Scenario → test map`, mapping every delta scenario to a named test or
`n/a: <reason>`.

## Architect review

After `tasks.md`, the planner reviews proposal, specs, design, and tasks against principles
§I–VII. Claude may invoke `architect-reviewer`; Codex performs a stated self-review. Write
`architect-review.md` with `## Verdict`, `## Findings`, and `## Scenario coverage`.

A simpler design, a missing scenario mapping, a Group 1 omission without `no RED`, a
platform fact asserted, not observed, a replaced input without the Design lists, or a
catcher the review cannot trace is a finding. Findings point at artifacts instead of
restating them. On `rework`, answer every finding and review again. On `approve`, when the
change has no issue ask once for priority and run `python <skill>/scripts/create_tracking_issue.py
<change> --priority <High|Medium|Low>`; otherwise run it without priority. The issue must be
`Planned` before the plan is ready.

## Install

Collect required `--test` and optional `--setup` literal shell commands. Run:

```text
python <skill>/scripts/init.py --setup "<command>" --test "<command>" --dry-run
python <skill>/scripts/init.py --setup "<command>" --test "<command>" --confirm-remote
```

The dry run shows the full local and remote plan without writing. The confirmed run
initializes pinned OpenSpec for Claude and Codex, merges the pointer rules and two Claude
plugin keys, writes the one caller and Dependabot entry, updates the versioned Codex
checkout/link, upserts the no-bypass ruleset, and copies/links Project 4 when none is linked.
It prints, but never performs, secret entry, Codex automatic-review setup, or Project UI
choices. Treat every conflict as a stop; never replace consumer-owned content.
