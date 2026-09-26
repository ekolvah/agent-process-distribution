## Why

[Install](../../../../skills/agent-process/SKILL.md#install) step 5 says "Once the first PR shows
`agent-process / quality`, run `activate_protection.py --pr <N>`". In a fresh repository the
first PR is the installation PR, and on it the run refuses (#183, observed in
`ekolvah/agent-process-sandbox#1` during #117 step 7a):

```
refused: caller absent on main: .github/workflows/agent-process.yml
exit=2
```

Root cause: the step omits an order the `distribution` requirement "Protection activation
observes quality first" enforces — the default branch must carry the caller, which it does
only after the installation PR is merged. The refusal is correct; the step is wrong.

Observed after the merge (issue comment of 2026-09-25): `activate_protection.py --pr 1
--dry-run` against the merged installation PR plans the ruleset create and exits 0, so no
second PR is needed.

## What Changes

- Step 5 states the order: after the person merges the installation PR, run
  `activate_protection.py --pr <N>` with that PR's number. The rest of the step (dry-run,
  ask once, `--confirm`, the review check) is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — procedure wording only; the enforced behaviour is already in `distribution`. The
change sets `skip_specs: true`.

## Impact

- Edited: `skills/agent-process/SKILL.md` (Install step 5).
- Not edited: `activate_protection.py` and its tests (behaviour is correct);
  `openspec/specs/distribution/spec.md`; archived changes (records of their time); no other
  doc names this step.
