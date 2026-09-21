## Context

The v1 resolver re-ran a dedicated required review workflow so that it could observe a
resolved blocking thread. Issue 112 removes that gate: quality is the only required job,
and the same `agent-process` workflow also runs advisory Claude review.

## Decision

The resolver still verifies that the workflow on the pushed head has settled, then
resolves the exact addressed older-head P0/P1 thread and replies. It does not re-run the
workflow because neither required quality nor advisory review depends on resolved-thread
state, while a full rerun starts another advisory review after the prescribed wait.

The run lookup remains a pre-write guard. A missing or running head workflow refuses the
operation; a reply failure after resolution prints the exact remaining API call.

## Risks / Trade-offs

- The resolved state is not represented by a new check run. This is intentional because
  v2 review is advisory; the person inspects current-head reviews and open threads.
- Resolution and reply remain two writes. The recovery message covers the partial window.

## Migration Plan

Remove only the rerun transport and its recovery branch, retain the settled-run guard,
update the target scenario and archived issue-112 decision, then archive this correction
in the existing issue-112 PR.
