## Why

Issue 112 combines required quality and advisory Claude review in one workflow. The
older thread resolver re-runs that entire workflow after resolving an addressed P0/P1
thread, which starts a duplicate advisory review on an unchanged head after the final
wait and can publish findings after handoff.

## What Changes

- Keep the settled current-head workflow precondition before resolving a P0/P1 thread.
- Resolve and reply without re-running the combined workflow on the unchanged head.
- Preserve explicit recovery when the reply fails after the irreversible resolve.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `implementation`: define thread closure for the combined v2 workflow without a
  post-resolution workflow re-run.

## Impact

Edits the portable resolver and tests, the implementation spec, and the archived
issue-112 design/scenario map. It does not change quality, review triggers, or protection.
