## Why

The per-task telemetry change (#101) waits for a backend decision
([ADR 0029](../../../../.agent-process/docs/adr/0029-telemetry-leaves-the-v2-migration.md)).
Langfuse models a task natively (trace, generations, tool calls, usage per observation)
and ships an official Claude Code plugin; the incumbent Grafana stack reconstructs a task
from labels. Issue 103 asks for a bounded spike that answers one fixed criterion before any
number is read. Its v1 plan is void: Codex is gone
([ADR 0033](../../../../.agent-process/docs/adr/0033-claude-code-is-the-only-carrier.md)) and
the #101 launcher that was to mint `task_id` / `attempt_id` waits for this spike.

Observed on 2026-10-07 in the Langfuse integration page
(`langfuse.com/integrations/other/claude-code`): the plugin is
`langfuse/Claude-Observability-Plugin`, a `Stop` hook that reads the transcript and sends
"user inputs and prompts, assistant responses and reasoning, tool inputs and outputs";
configuration is `TRACE_TO_LANGFUSE`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`,
`LANGFUSE_BASE_URL`; assistant messages are "deduplicated by `message.id`"; the trace
carries `session_id` and the tag `claude-code`, and no variable for custom tags or metadata
is documented. The spike verifies these against the pinned source, not the page.

## What Changes

- Vet the plugin at a pinned commit and its `langfuse` SDK at a pinned version (digest
  verified, hook scripts read for what they send and where), recording both in `evidence/`.
- The owner chooses Langfuse Cloud or self-hosted against the vetted payload, recorded before
  the first trace.
- Run at least three real tasks of this repository with tracing on; cross-check each
  session's totals against `ccusage` for the same session id.
- Read M1, M3, M4, M5 and M6 (#99) per task in Langfuse with no code beyond the plugin and
  its configuration.
- Record the outcome in one ADR, "per-task token analysis backend": criterion, readings,
  verdict, reconsider condition. Post the verdict on #101 and #99.
- Dropped from issue 103: AC6 (Codex route) — no Codex carrier exists. AC3 is reframed: no
  launcher mints `task_id` yet, so the spike tests whether the plugin can carry a
  launch-environment identifier at all, and records the answer as a finding.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true`: the spike changes no process behaviour; its product is an ADR.

## Impact

- Added: `.agent-process/docs/adr/0036-per-task-token-analysis-backend.md`.
- Edited, removed: none in the tree. For the spike window only, the owner host carries the
  plugin's local marketplace clone and readings under Git-ignored `evidence/`, its
  `pluginConfigs` entry in `~/.claude/settings.json`, the secret in the credential store, and
  the local-scope install plus `UV_EXCLUDE_NEWER` in the untracked
  `.claude/settings.local.json` of the main checkout; all are removed at the end.
- External: a Langfuse project (Cloud or self-hosted, per the owner's choice) receives
  transcripts of the measured sessions only.
- Not touched: Grafana dashboards and `.agent-process/docs/telemetry-measurement-setup.md`
  (#101 rewrites them against the chosen backend).
