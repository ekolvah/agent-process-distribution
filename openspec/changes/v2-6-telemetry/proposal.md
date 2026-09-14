## Why

"v2 is no worse than v1 on tokens" needs numbers per merged PR, not raw sums. Both agents
export OpenTelemetry; an owner-side collector with task labels is enough.

## What Changes

- Owner-side OTLP collector and launcher attaching project, task and attempt labels;
  reports per merged PR by role, cycle time, review rounds, share merged without a fixer
  commit, agent turns per issue.
- Nothing is shipped to consumers.

## Capabilities

### New Capabilities
- `telemetry`: owner-side token-efficiency measurement.

### Modified Capabilities
<!-- none -->

## Impact

- Added: `telemetry/` (collector config, launcher, report), outside the plugin.
