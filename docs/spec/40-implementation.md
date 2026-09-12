# Implementation

**Question this document answers:** how the process gets correct implementations out of
agents, how rework after CI is kept low, and how an agent turn ends.

Status: draft

## Requirements

- **IMPL-1** (MUST) RED first for behavioural changes: the implementer writes the failing
  test from the issue's `## Test plan` and proves it red with `check_red` before writing
  code. Documentation-only, rename and one-line non-behavioural changes are exempt
  (`principles.md` §I). The project's test-runner command is declared in `AGENTS.md`; the
  only requirement on it is an exit code.
- **IMPL-2** (MUST) The project's `ci_check` is the single source of truth for quality
  checks; the pre-push git hook and the reusable workflow run the same command.
- **IMPL-3** (MUST) Branch and PR use GitHub's own linking: `gh issue develop -c N`
  creates the linked branch, the PR links to the issue automatically, the merge closes it.
- **IMPL-4** (MUST) Shift-left feedback in Claude: a PostToolUse hook runs the linter for
  the edited file's extension right after the edit, and a PreToolUse hook gives the
  cheaper navigation route when a shell command reads a file.
- **IMPL-5** (MUST) The `implement-issue` skill ends only after the PR's checks and
  reviews are in. The last step is one blocking script, `wait_for_pr`, that waits on
  `gh` for checks and review threads and prints the unresolved ones. Prose ("stay active")
  is not a gate.
- **IMPL-6** (SHOULD) A Stop hook blocks the end of a turn only when the current branch
  has an open PR with pending checks or unresolved threads, and names the next command.
- **IMPL-7** (MUST) Principles (`principles.md`) reach the agent through the plugin's
  rules as one short file.
- **IMPL-8** (MUST NOT) No per-project test-runner adapter in the core; no budgets
  (`max_runs`) or delivery state file; no Codex-side hooks.
