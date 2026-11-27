## Why

`openspec archive` writes a placeholder Purpose into the main spec of every capability a change
creates without a `## Purpose` in its delta, and nothing in the process fails on it: the Verify
group validates before the archive, CI does not run OpenSpec at all, and the change is gone by
the time the placeholder appears. Observed in a consumer (agent-process 3.34.1, openspec 1.13.0):
three green PRs left three main specs with
`TBD - created by archiving change <name>. Update Purpose after archive.`, and
`openspec validate --strict --all` on its default branch reports `7 passed, 3 failed`.

Reproduction (openspec 1.13.0, scratch project, one change creating `alpha` with a delta
`## Purpose`, one creating `beta` without):

- `openspec validate --strict --all` before the archive: `✓ change/no-purpose`,
  `✓ change/with-purpose`, `Totals: 2 passed` — a change missing the Purpose validates.
- After `openspec archive <change> -y` for both: `openspec/specs/alpha/spec.md` carries the
  delta's Purpose verbatim; `openspec/specs/beta/spec.md` carries
  `TBD - created by archiving change no-purpose. Update Purpose after archive.`
- `openspec validate --strict --specs`: `✗ spec/beta` — `Purpose section is still a placeholder
  rather than a Purpose anyone wrote`, rc=1.

Root cause: "update Purpose after archive" lives only as text inside the placeholder; no script
or check owns it, and the one script that runs the archive, `archive_change`, does not validate
what the archive writes.

## What Changes

- `archive_change` adds the step the stock `/opsx:archive` flow has and the bare CLI skips
  (`openspec-sync-specs` step 5, "Validate updated main specs"): after `openspec archive -y` and
  before the commit it runs `openspec validate --strict` on each main spec the change has a
  delta for, and exits 2 with OpenSpec's findings when one fails, nothing committed or pushed.
  The fix is a direct edit of the placeholder Purpose, as OpenSpec's warning says; a re-run
  finds the archive uncommitted and continues from the validation.
- `SKILL.md` Delivery allows the one direct edit of `openspec/specs/` OpenSpec requires: replacing
  a placeholder Purpose.
- No new planning guidance: `openspec instructions specs` already tells the planner to open a new
  capability's delta with `## Purpose`; the gap is enforcement.

## Capabilities

### New Capabilities

### Modified Capabilities
- `implementation`: requirement `archive_change archives the change before its PR` gains the
  refusal to commit an archive whose main specs do not validate, and the re-run that resumes it.

## Impact

- Edited: `skills/agent-process/scripts/archive_change.py`, `skills/agent-process/SKILL.md`.
- Edited: `tests/publisher/test_pr_delivery.py`, `tests/publisher/test_planning_workflow.py`.
