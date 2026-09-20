## Why

The issue-112 pull request reproduced a GitHub Actions bootstrap failure: the publisher caller passed the
new `setup` and `test` inputs to `reusable-quality.yml@main`, but `main` still exposes the
old no-input interface until this PR merges. GitHub rejected the workflow before creating
jobs, so the required `quality / quality` context could never exist.

## What Changes

- Give the publisher a narrow bootstrap exception: its caller uses the reusable workflow
  from the same commit through a local reusable-workflow reference.
- Keep every installed consumer caller pinned to the immutable process tag.
- Record that the publisher's local call is protected by current-head workflow inspection,
  not by a separately pinned callee.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: distinguish the publisher's self-hosting bootstrap reference from the
  immutable tag required in installed consumer callers.

## Impact

Edits `.github/workflows/agent-process.yml`, its publisher contract test, the archived
issue-112 design/scenario map, and the distribution spec. The consumer template,
installer, ruleset, dependencies, and external state do not change.
