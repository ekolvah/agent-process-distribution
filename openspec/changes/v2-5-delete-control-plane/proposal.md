## Why

After v2-1 … v2-4 the orchestrator, delivery state, role catalogue and run budgets protect
nothing that the person, the ruleset or the Project does not already decide. Deleting them
is what makes the size budget hold.

## What Changes

- **BREAKING**: `agent_orchestrator.py`, `delivery_state.py`, `roles.yaml`, `max_runs`
  budgets, Codex-side hooks and their tests are deleted; `.agent-process/docs/architecture/`
  is reduced to `principles.md`.
- The remaining core follows the maintenance rules: stack-agnostic, justified by repeated
  failure, deterministic rules in scripts, size budget, no internal API compatibility.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `maintenance`: adds the rules that keep the core small.
- `implementation`: adds the no-budgets rule.

## Impact

- Removed: ≈ 2 600 lines of scripts and ≈ 5 000 lines of tests.
- `agent-process.md` and `agent-process-installation.md` deleted; `README` points to the
  plugin, the skills and `openspec/specs/`.
