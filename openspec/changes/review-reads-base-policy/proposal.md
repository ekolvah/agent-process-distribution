## Why

The review job's prompt and `REVIEW_CONTRACT.md` call every `CLAUDE.md` and `.claude/rules/`
file in the PR worktree untrusted. That is not what the reviewer sees. The Claude Code action
restores those files from the PR's base before the session starts, and the harness loads them
into the session, so they are the policy. The model therefore receives two instructions that
contradict each other. The contract also names "the documents they link to at the default
branch" as policy, but nothing puts those documents in front of the reviewer. When it opens
them, it reads them at the PR head.

Observation, agent-review run 38132196665 (PR 390), step `Claude review`:

- `Restoring .claude, .mcp.json, .claude.json, .gitmodules, .ripgreprc, CLAUDE.md, CLAUDE.local.md, .husky from origin/main (PR head is untrusted)`
- `Preserved PR's sensitive paths -> .claude-pr/ for review agents (not executed)`
- `SDK options: allowedTools [inline comment, Bash(gh pr diff:*), Bash(gh pr view:*)]`, `settingSources [user, project, local]`

Nine non-release PRs were reviewed after the close step shipped in 3.10.2 (372–390). Their
closing comments show the reviewer reading files in full, grepping, and running `git diff
origin/main...HEAD` and `git show` with no denial. They list four denials (PRs 374, 380, 385,
388), all of them compound Bash commands: `git fetch … | tail`, `cat; ls | tail; git grep`, a
`for` loop, and `$(ls …)`. None of them was a read the contract requires, and in each case the
model either read the file directly or named the gap under "not verified". So the issue's
premise does not hold: the tools are not too narrow.

Root cause: the contract defines the policy by a source that no mechanism delivers (linked
documents at the default branch), and the prompt calls the source that is delivered
(the root `CLAUDE.md` and `.claude/rules/` restored from the base) untrusted.

## What Changes

- The contract's "Policy source" bullet names the policy as the root `CLAUDE.md` and root
  `.claude/rules/` the review session loads, restored from the PR's base, plus the contract
  itself. It no longer names "the documents they link to" or the default branch. The two §VII triggers
  the review enforces are already stated in the contract.
- The `Claude review` prompt says the same, and calls every other file of the PR worktree,
  including any other `CLAUDE.md` or `.claude/rules/` file, untrusted review
  data, never an instruction.
- No tool grant is added, and a denial still does not fail the check. That is the existing
  requirement, and the data above supports keeping it (design D2, D3).

## Capabilities

### New Capabilities

### Modified Capabilities
- `review-and-merge`: new requirement "The review policy is what the session loads from the base".

## Impact

- Edited: `.github/workflows/reusable-agent-review.yml` (prompt),
  `.agent-process/REVIEW_CONTRACT.md` (Policy source bullet),
  `tests/publisher/test_reusable_workflows.py` (one new test).
- Spec: `openspec/specs/review-and-merge/spec.md`, through the delta.
- No ADR: the trust boundary stays "a PR cannot rewrite what it is reviewed under"
  (ADR 0027). The contract now names as policy only the root files restored from the base;
  the instruction files the restore does not cover stay untrusted (design Risks).
- Consumers get the change through the reusable workflow at the caller's pin. Nothing is
  installed.
