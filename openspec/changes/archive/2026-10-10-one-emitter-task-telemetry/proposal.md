## Why

Per-task numbers come from two emitters today: Claude Code's own OpenTelemetry metrics go to
Grafana, and the Langfuse plugin's transcript hook goes to Langfuse. They cannot agree on
totals: the hook double-sends after `EnterWorktree` and drops a session silently on a
SessionEnd timeout ([ADR 0036](../../../../.agent-process/docs/adr/0036-per-task-token-analysis-backend.md)).
No session carries a task identity on the Grafana side either, so per-task metrics (#99)
cannot be computed there. The root cause is that the identity does not exist before the
exporter starts, and that only one of the two backends is fed by the exporter itself.

Observed on 2026-10-10, Claude Code 2.1.295, an interactive CLI session (new console,
`terminal.type` `mingw64`, `query_source_safe` `repl_main_thread`) with
`CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` and `OTEL_TRACES_EXPORTER=otlp` pointed at a local
capture (summary in Git-ignored `evidence/issue-101/traces-probe-2026-10-10.json`):

- Traces export from an interactive session on this account: `claude_code.interaction`,
  `claude_code.llm_request`, `claude_code.tool`, `claude_code.tool.execution` and
  `claude_code.tool.blocked_on_user` arrived. The documentation's allowlisting condition
  ("In interactive CLI sessions, detailed beta tracing also requires your organization to be
  allowlisted", code.claude.com/docs/en/monitoring-usage) did not block these spans.
- `claude_code.llm_request` carries `input_tokens`, `output_tokens`, `cache_read_tokens`,
  `cache_creation_tokens`, `gen_ai.request.model` and `session.id`; it carries no
  `gen_ai.usage.*` attribute.
- The process-environment `OTEL_RESOURCE_ATTRIBUTES=task_id=probe-101,...` did not reach the
  resource: the project's `.claude/settings.json` value replaced it. An additional
  `--settings` layer did carry `task_id` and `attempt_id` (console exporter, Claude Code
  2.1.269, issue 101 comment of 2026-09-12).

Langfuse maps usage from `gen_ai.usage.*` or `langfuse.observation.usage_details` only, and
infers `generation` from a model attribute such as `gen_ai.request.model`
(langfuse.com/integrations/native/opentelemetry, "Attribute Mapping"). The spans therefore
need a collector transform before Langfuse can show their usage. That Langfuse then reads
the usage correctly is the first live gate of this change, and if it fails the change exits
early.

## What Changes

- Owner launcher `.agent-process/scripts/task_session.py`: `--issue N [--attempt K] --
  <claude command>` adds one `--settings` JSON layer. Its `OTEL_RESOURCE_ATTRIBUTES` is the
  project's own value plus `task_id=issue-N,attempt_id=K` and a per-launch
  `service.instance.id`, and it turns on the traces beta
  for that session only.
- Owner host: traces of launched sessions go to the local Alloy receiver. Alloy maps the
  token attributes to Langfuse usage details, adds the task and attempt as Langfuse trace tags,
  and exports to Langfuse's OTLP endpoint. The dead Codex metric chain leaves `config.alloy`,
  and `run-alloy.ps1` requires the Langfuse keys instead of the Codex route's variables. Metrics and logs keep their direct route to
  Grafana and get the task identity from the same resource attributes.
- Once one task's Langfuse usage equals its Grafana token totals, the Langfuse plugin is
  uninstalled.
- ADR 0037 records the decision. The measurement setup document describes the traces
  route and the launcher, and drops the Codex route, which no longer exists
  ([ADR 0033](../../../../.agent-process/docs/adr/0033-claude-code-is-the-only-carrier.md)).
- Dropped from the v1 plan in the issue: Codex codec, attempt ledger, outcome resolver
  (#99 derives outcomes from PRs), collector-side `unassigned` label for metrics, temporary
  settings file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `skip_specs: true`: the launcher and the collector route are owner-side measurement
tooling, not process behaviour. No consumer receives them.

## Impact

- Added: `.agent-process/scripts/task_session.py`, `tests/agent_process/test_task_session.py`,
  `.agent-process/docs/adr/0037-one-emitter-feeds-both-telemetry-backends.md`.
- Edited: `.agent-process/docs/telemetry-measurement-setup.md`.
- Removed: none in the tree. Draft PR 104 (v1 launcher) is closed as superseded.
- Owner host, outside the tree: `~/.config/alloy/config.alloy` gains a traces pipeline;
  the User-scope environment gains the Langfuse keys that Alloy reads; the Langfuse plugin is uninstalled.
- External: Langfuse Cloud (EU) receives spans of launched sessions only, with account
  fields (`user.email`, `organization.id`). Prompt text is `<REDACTED>`, and no tool input
  or content is sent.
