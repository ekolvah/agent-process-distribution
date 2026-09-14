## Why

v1 classifies review outcomes, publishes evidence, preflights credentials and fails over
between reviewers in a state machine, and keeps delivery state in a process-owned file.
GitHub already provides review apps, conversation resolution and a Project with status
automations.

## What Changes

- Codex GitHub app and a short `claude-code-action` workflow review every PR on open;
  verdicts are advisory, threads block through the ruleset.
- The GitHub Project's `Status` and built-in automations are the only delivery state;
  `set_status` moves an item to In progress.
- Cycle time from In progress to mergeable contains no human step and is measured per PR.
- **BREAKING**: `request_codex_review.py`, `review_gate.py`, `install_branch_protection.py`,
  `bootstrap_github_project.py`, `project_settings.py` and their tests are deleted.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `review-and-merge`: adds advisory review, reviewer instructions, later-fix flow, no state machine.
- `state`: adds Project status as the lifecycle field, automations, `set_status`, readability.
- `implementation`: adds the cycle-time requirement.

## Impact

- Added: `.github/workflows/agent-process.yml` review job, `scripts/set_status.py` wiring.
- Removed: review pipeline and Project bootstrap scripts (≈ 2 500 lines with tests).
