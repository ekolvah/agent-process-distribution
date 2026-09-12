# Review and merge

**Question this document answers:** what reviews a PR, what blocks a merge, and how the
process protects the default branch from agent mistakes.

Status: draft

## Requirements

- **REVW-1** (MUST) PR review is **advisory**: the Codex GitHub app reviews every PR by
  its own configuration, and a short `claude-code-action` workflow (~30 lines) reviews the
  diff. Neither verdict is classified by a script or turned into a required check.
- **REVW-2** (MUST) The reviewer reads the **diff** of the PR, not whole files, and the PR
  body lists tracked deferrals as issue links so a reviewer does not re-report them.
- **REVW-3** (MUST) The implementer's own run applies review findings before the person
  looks (`40-implementation.md`, IMPL-5); a later fix is the person launching
  `/implement #N` again, which reads the open threads.
- **REVW-4** (MUST) The only automated merge gates are GitHub-native: required checks
  from the reusable workflow, `required_conversation_resolution`, PR required, no direct
  push. They are applied as a ruleset JSON kept in this repository and installed once by
  `init`.
- **REVW-5** (MUST) The person merges. No agent has merge authority.
- **REVW-6** (MUST) Local safety is a deny-list in the plugin's `settings.json`
  (force-push, push to the default branch); the ruleset is the authoritative barrier.
- **REVW-7** (SHOULD) Reviewer instructions name the two simplicity triggers of ADR 0016
  (reinvented functionality, unnecessary complexity) as findings to raise.

## Rationale

v1 made review a required check with its own state machine: an owner comment `@codex
review`, a workflow that read the review, classified it (clean / rework / blocking), fell
back to Claude when Codex was unavailable, published evidence, and a `review_gate.py` that
decided whether the fix loop continued (up to three fixer runs) — about 2 100 lines of
scripts and 276 lines of workflow. With a person merging, the red check duplicated the
human decision, and the failover existed to protect a gate that need not be a gate.

What is given up: the automatic red check on a BLOCKING finding, the advisory/blocking
distinction between threads (`required_conversation_resolution` treats every thread the
same — the person or the agent resolves advisory ones too), and carrier failover.

ADR 0020's lesson (the same deferred finding re-reported for four rounds, budget exhausted)
came from reviewing whole files without memory; REVW-2 removes the cause rather than
adding a downgrade channel.

`install_branch_protection.py` and `check_branch_protection.py` (890 lines) become a JSON
file plus one `gh api` call; drift is visible because the required check is one job that
either runs or does not.

## Non-goals

- Outcome classification, evidence publishing, review credentials preflight.
- Carrier failover between reviewers.
- A drift check for branch protection.

## Open questions

- Confirm the Codex GitHub app reviews on PR open without a trigger comment on the
  current plan; settled by one observed PR.
- Whether the Claude review workflow runs on every push or only on `ready_for_review`.

## Traceability

- ADR 0003, 0004, 0014, 0015, 0020, 0022, 0023 — superseded by this spec once v2 lands.
- ADR 0016 — criterion kept as REVW-7, mechanism dropped.
- `REVIEW_CONTRACT.md` — becomes the reviewer instruction text referenced by REVW-7.
