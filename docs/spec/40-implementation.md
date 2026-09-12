# Implementation

**Question this document answers:** how the process gets correct implementations out of
agents, how rework after CI is kept low, and how an agent turn ends.

Status: draft

## Requirements

- **IMPL-1** (MUST) RED first: the implementer writes the failing test from the issue's
  `## Test plan` and proves it red with `check_red` before writing code. This is the one
  "smart" gate the core keeps. The project's test-runner command is declared in
  `AGENTS.md`; the only requirement on it is an exit code.
- **IMPL-2** (MUST) The project's `ci_check` is the single source of truth for quality
  checks; the pre-push git hook and the reusable workflow run the same command.
- **IMPL-3** (MUST) Branch and PR use GitHub's own linking: `gh issue develop -c N`
  creates the linked branch, the PR links to the issue automatically, the merge closes it.
- **IMPL-4** (MUST) Shift-left feedback in Claude: a PostToolUse hook runs the linter for
  the edited file's extension right after the edit (~100 lines), and a PreToolUse hook
  gives the cheaper navigation route when a shell command reads a file (~80 lines).
- **IMPL-5** (MUST) The `implement-issue` skill ends only after the PR's checks and
  reviews are in. The last step is one blocking script, `wait_for_pr`, that waits on
  `gh` for checks and review threads and prints the unresolved ones. Prose ("stay active")
  is not a gate.
- **IMPL-6** (SHOULD) A Stop hook of ~40 lines blocks the end of a turn only when the
  current branch has an open PR with pending checks or unresolved threads, and names the
  next command. No budgets, no state file; a looping agent is visible on the PR.
- **IMPL-7** (MUST) Principles (`principles.md`) reach the agent through the plugin's
  rules as one short file, not through a 1 200-line canon.

## Rationale

ADR 0021 recorded the failure: the agent returned before the PR existed, and "stay active
until the gate ends the loop" existed only as prose. v1 answered with a Stop hook that
read CI stamps, gate stamps and a budget ledger via `delivery_state.py`. IMPL-5 answers
the same failure with "a script instead of an instruction" and no state machine: the skill
cannot finish before `wait_for_pr` returns. IMPL-6 keeps the observable part of ADR 0021
at a fraction of the size.

`open_pr.py` (363 lines) and `verify_pr_link.py` (337 lines) exist because one issue once
stayed open after merge. `gh issue develop` makes the link a GitHub property of the branch
rather than a body-text convention; IMPL-3 removes both scripts plus `issue_branch.py`,
`new_branch.py` and `update_pr_body.py`.

Rework metrics live in `70-telemetry.md`: review rounds per PR, share of PRs merged without
a fixer commit.

## Non-goals

- A per-project test-runner adapter in the core.
- Budgets (`max_runs`) or a delivery state file.
- Codex-side hooks (`20-roles.md`).

## Open questions

- Confirm that a PR from a `gh issue develop` branch auto-closes the issue on merge in a
  private repository; settled by one observed merge recorded in the v2 ADR.
- Whether `wait_for_pr` also polls the Codex review app or only the checks and threads.

## Traceability

- ADR 0021 (end of turn is gated) — mechanism replaced by IMPL-5/IMPL-6.
- ADR 0016 (review gate blocks on simplicity) — the criterion moves to the reviewer
  instructions; see `50-review-and-merge.md`.
- `check_red.py`, `ci_check.py` — kept; `hooks.py`, `navigation_policy.py` — trimmed to
  IMPL-4/IMPL-6.
