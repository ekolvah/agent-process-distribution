## Why

[`REVIEW_CONTRACT.md`](../../../../.agent-process/REVIEW_CONTRACT.md) does not name `principles.md`,
so a diff that breaks §II–VI passes unless "convention violation" happens to catch it.
Observed: the review of PR #426 (run 38692248603) lists what it read — the trusted contract,
`CLAUDE.md` and `.claude/rules/workflow.md` — and not `principles.md`, although the trusted
checkout holds it and `CLAUDE.md` links it.

## What Changes

- The contract's policy source names `trusted/skills/agent-process/principles.md`, apart from the PR worktree's copy, and its
  `P0`/`P1` convention-violation class names, per §I–VI, the breach a diff shows.
- §VII's two narrow triggers and the rule that PR-worktree docs are data stay as they are.

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: the review contract labels a violation of each of §I–VI.

## Impact

- Edited: `.agent-process/REVIEW_CONTRACT.md`, `tests/publisher/test_reusable_workflows.py`,
  `openspec/specs/review-and-merge/spec.md`.
- Added, removed: none; the review job's prompt and workflow stay as they are.
