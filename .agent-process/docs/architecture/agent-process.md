# Agent development process

**Question this document answers:** What operational boundary surrounds the shared
agent-process skill in a repository using GitHub, OpenSpec, Claude Code, and Codex?

The portable procedure lives once in
[`skills/agent-process/SKILL.md`](../../../skills/agent-process/SKILL.md). This page explains
the repository contract and trust boundary; it does not copy the skill's task recipe.
OpenSpec specs describe current behaviour, pending changes describe the next behaviour,
ADRs explain decisions, and Git history preserves the old mechanisms.

## Roles and hand-offs

| Role | Required result | Next role |
| --- | --- | --- |
| planner | validated change, `architect-review.md` starting with `approve`, tracking issue in `Planned` with priority | person approval, then implementer |
| implementer | issue-linked branch, RED evidence, implementation, archived change, PR | advisory reviewers |
| reviewer | visible findings or a clean result on the current head | fixer or person |
| fixer | minimal class-level correction and a new settled-head wait | reviewer or person |
| person | approve the plan; inspect workflow/review state; merge or decline | terminal |

Any Claude or Codex adapter may fill a role if it follows the same skill and produces the
same artifacts. Agent prose is not a gate: script exit codes, the required quality check,
and the person's decisions are the evidence.

## Planning

Planning uses the stock OpenSpec `spec-driven` schema. `openspec/config.yaml` keeps local
context and points proposal, specs, design, tasks, and architect review to the shared skill.
The plan lives under `openspec/changes/<change>/`.

## Issue contract

The GitHub issue carries the change name, Project Status, and Priority. The propose tail writes the issue number into the first
`tracking issue <N>` token and sets `Planned`.

The person approves a plan by starting apply. The first apply task runs
`skills/agent-process/scripts/start_change.py`; it refuses an unfinished propose run or a
non-approve verdict before it creates a branch. The branch created by `gh issue develop`
provides GitHub's native PR-to-issue link. The required quality workflow fails when that
link is absent.

## Deterministic delivery flow

The **Tasks** section of the shared skill is canonical. At a high level:

1. `start_change.py` validates the handoff, creates the linked branch, sets `In Progress`,
   and records planner/implementer provenance.
2. `check_red.py` proves behavioural tests fail before implementation. It owns the pytest
   invocation and JUnit report so caller conventions cannot silently shorten the run.
3. The implementer makes focused changes, runs the repository's complete quality command,
   and validates OpenSpec strictly.
4. `archive_change.py` archives and pushes the change before the PR opens, so the reviewed
   head contains the plan and implementation together.
5. The PR opens from the linked branch. `wait_for_pr.py` waits until every check on one
   settled head concludes, then prints unresolved review threads. Fix/answer rounds are
   bounded to three; `resolve_review_thread.py` is only for a P0/P1 thread addressed by a
   newer pushed correction.
6. The implementer inspects every current-head `.github/workflows/**` diff and visible
   advisory review state, then hands the PR to the person without merging.

For the issue 112 transition only, the old default branch still governs the start of the
run. Its PR request is therefore made once with
`.agent-process/scripts/request_codex_review.py` before the new process is merged. This is
transition evidence, not a path consumers retain and not a second portable procedure.

## Quality and workflow trust

The consumer owns literal setup and test commands in one thin
`.github/workflows/agent-process.yml` caller. Its `quality` job invokes the tagged reusable
workflow from this repository. The callee checks the PR-to-issue link, checks out the exact
PR head, runs setup when non-empty, runs the test command, and validates OpenSpec strictly
when `openspec/` exists. A command typo or non-zero exit is visible and red.

The repository ruleset requires a pull request, strict `quality / quality` from GitHub
Actions integration 15368, and blocks deletion and non-fast-forward updates of the default
branch. It has no process bypass actor.

This is a name-bound status check. A PR can edit its caller, omit a repository gate, or try
to report the same context name. The pinned callee is not editable by that PR, but a
repository ruleset on a personal repository does not authenticate which caller selected
it. The terminal human inspection of current-head workflow diffs is therefore a deliberate
part of the merge boundary. An organization may add a required-workflow rule as a stronger
external anchor.

## Review outcome enforcement

There is no process-owned review outcome gate in v2. Review is visible evidence for the
person, while the required machine gate is quality.

## Review gate verdicts

The publisher temporarily retains the v1 `review_gate.py` verdicts for changes already
scheduled on that process. They are a compatibility surface during the migration, not a
v2 required check or a distributed consumer contract.

## Advisory review

The caller invokes `anthropics/claude-code-action@v1` directly. The person enables Codex
automatic reviews in the Codex GitHub settings. Both publish ordinary visible review
comments independently; neither is parsed, used as a fallback, requested by a process
comment, or made a required status check. A failed Claude job remains visible, but review
absence or an unresolved severity label does not masquerade as a machine-enforced verdict.
The person decides whether findings are sufficiently addressed.

## Distributed and publisher-only boundaries

Consumers receive only OpenSpec-generated Claude/Codex files plus `openspec/config.yaml`,
two Claude plugin settings keys, one workflow caller, and one Dependabot entry. The Codex
skill is linked at user scope. Consumers do not receive `.agent-process/`, hooks,
`AGENTS.md`, a review contract, report-path conventions, or process tests.

This publisher temporarily retains v1 scripts, hooks, and repository-specific settings
needed by changes scheduled after issue 112. Their presence here is not distribution. The
publisher dogfoods the shared skill, pointer rules, one caller, and reusable quality
workflow before releasing version 2.0.0.

## Governance conventions

- One PR is one logical unit; unrelated infrastructure repair gets its own issue.
- Ask priority once when the tracking issue is created. The process writes only `Planned`
  and `In Progress`; Project workflows own `Todo` and `Done`.
- Never push directly to the default branch, force-push, hard-reset, force-delete an issue
  branch, bypass checks, or self-merge.
- A spec correction uses a delta and archive. A changed archived design decision is amended
  with its scenario map in the same push.
- If a requirements input changes, regenerate its matching lockfile in the same commit.

## Terminal state

The implementation run is complete only after the current head has concluded checks,
unresolved threads have been addressed or explicitly left to the person within the round
budget, workflow diffs and advisory review state have been inspected, and the PR is handed
off without merge. The human merge remains the final authority.
