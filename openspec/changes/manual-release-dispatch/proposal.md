## Why

Only the nightly `schedule` run opens or updates the release PR (ADR 0047), so a merged
feature reaches `stable` the next night at the earliest. On 2026-11-15 the person needs
`feat: init-sets-review-secret (#517)`, merged after v3.33.0, released today to install the
plugin into a new project. The release workflow has no manual trigger (observed:
`gh workflow run release-please.yml --ref main` → `HTTP 422: Workflow does not have
'workflow_dispatch' trigger`), and the nightly-release-merge design deferred one only because
"nothing observed needs one". Now one does.

## What Changes

- `.github/workflows/release-please.yml` gains a `workflow_dispatch` trigger. A dispatched run
  behaves as the scheduled run: it opens or updates the release PR, approves it and enables
  auto-merge; its merge's push run creates the release and moves `stable`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: "Releases go through release-please" — a manual dispatch also opens or
  updates the release PR.

## Impact

- Edited: `.github/workflows/release-please.yml`,
  `tests/publisher/test_reusable_workflows.py`, `.agent-process/docs/adr/0047-release-prs-merge-nightly.md`
  (manual dispatch as an accepted daytime exception), `openspec/specs/distribution/spec.md` (via archive).
- No dependency, script or consumer-template change: consumers do not install
  `release-please.yml`.
