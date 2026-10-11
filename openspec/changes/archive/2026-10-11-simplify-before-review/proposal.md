## Why

The architect review approves plans that duplicate what the repository already has, and the
implementation reaches the PR without a reuse or simplification pass. Claude Code's bundled
`/simplify` closes both gaps, but it runs only when the person types it. Three manual runs on
2026-10-11 are recorded in the tracking issue (comment "Observed runs"):

- **Plans of two changes, run after `approve`.** It found a rule stated twice with two
  meanings, a copied check instead of an extended one, a bespoke secret grep duplicating
  detect-secrets, and a retry loop and queries that existing code already covered. Its edits
  also introduced three defects of one class: a silent default (0 or 1) in place of a missing
  value. The architect re-review caught each one (`rework`), at the cost of two extra rounds
  per plan.
- **Code of one PR, run after the PR opened.** It replaced an import of private names with a
  public function and merged duplicated paths. The CI review of the new head found nothing,
  and the head was reviewed one extra time.

Platform facts:

- `/simplify` "Review[s] the changed code for cleanup opportunities and appl[ies] the fixes.
  Four review agents run in parallel … The review doesn't look for correctness bugs … Pass a
  path or PR reference to review a specific target"
  ([commands reference](https://code.claude.com/docs/en/commands)).
- The agent can invoke it. The propose run of this change invoked `/simplify
  openspec/changes/simplify-before-review/` through the Skill tool on 2026-10-11, with the
  directory untracked. The skill printed `Review target:` with the argument verbatim, and its
  Phase 0 reads "If a PR number, branch name, or file path was passed as an argument, review
  that target instead"; without one it runs "`git diff @{upstream}...HEAD` (or `git diff
  main...HEAD` / `git diff HEAD~1` if there's no upstream)".
- `start_change` makes `origin/<change>` the branch's upstream (`git worktree add --track`
  from the branch `gh issue develop` creates on the default branch), and the archive is the
  first push. At Verify, the default diff is the branch's commits.

## What Changes

- The propose run runs `/simplify` on the change directory once, before the first architect
  review, so the review checks its edits in the same round. The plan's explanation states what
  it changed.
- Verify opens with `/simplify` without an argument, on the branch's commits, so the PR opens
  on the simplified head.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `planning`: a `/simplify` pass precedes the architect review.
- `implementation`: a `/simplify` pass opens Verify.

## Impact

- Edited: `skills/agent-process/SKILL.md` (`## Tasks` item 4, `## Architect review`),
  `tests/publisher/test_planning_workflow.py`.
- Added: none. Removed: none.
- Every propose and apply run of consumers costs one more pass of four agents (about
  190k–230k tokens observed per run).
