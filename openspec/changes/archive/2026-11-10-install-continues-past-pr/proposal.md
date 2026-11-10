## Why

Install ends at the installation PR: SKILL.md Install step 4 tells the person to merge it, and
steps 5 (`activate_protection`) and 6 (agent identity) start "once the person has merged it",
but no step carries the session from the opened PR to the merge. In a consumer install
(ekolvah/lampa-mediacenter#38) the session ended at the PR and step 6 was never run; the
`manual protection`, `agent-identity` and `auto-merge` rows (`install-reports-post-merge-steps`,
archived 2026-11-09) now report the gap, but only on the next `init` run.

Observed: `gh pr view 490 --json state` on this repository's merged PR prints
`{"state":"MERGED"}`.

## What Changes

- Install step 4 waits on the installation PR with `agent-process wait_for_pr <PR>`, fixes a
  failing quality check, shows review threads to the person, asks for the merge, reads
  `gh pr view <PR> --json state`, and on `MERGED` runs steps 5–6 in the same session.

## Capabilities

### Modified Capabilities
- `distribution`: a new requirement, `Install continues past the installation PR`.

## Impact

- Edited: `skills/agent-process/SKILL.md` (Install step 4),
  `tests/publisher/test_planning_workflow.py`, `openspec/specs/distribution/spec.md` (by
  archive).
- Added, removed: none.
- ADR: none applies. ADR 0040 (agent identity) and 0032 (review gate in every consumer) fix
  what steps 5–6 do, not when the session runs them.
