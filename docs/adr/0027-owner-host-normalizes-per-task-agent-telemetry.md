---
status: "accepted"
date: 2026-09-12
decision-makers: repository owner
consulted: —
informed: —
---

# The owner host normalizes per-task agent telemetry

## Context and Problem Statement

The token-efficiency experiment needs project, task, and attempt labels on
local Claude Code and Codex token metrics (#99). Sessions cannot stand in for
tasks: one session can cover several issues and one issue can span several roles
and sessions.

This measurement is intentionally private to the repository owner's Windows
workstation. It is not an agent-process feature for adopters. The question is
where to create task identity and where to normalize the two providers' different
OTLP resource shapes without leaking owner endpoints or policy into Copier and
the Claude plugin.

Before this decision, Claude sent metrics directly to Grafana Cloud while Codex
sent metrics through a local Grafana Alloy 1.18.1 process. Claude accepts independent
OpenTelemetry resource attributes; Codex exposes only one `otel.environment`
scalar. The existing Alloy transform already promoted that Codex scalar from the
resource onto metric datapoints as the project label.

## Decision Drivers

* Task identity must exist before the agent exporter starts.
* Both local CLI carriers must produce the same three Grafana label names.
* A bypass must be visible as `unassigned`, not inherit a previous task.
* Existing metric names, temporality, `job`, `instance`, Claude logs, and
  historical series must retain their meaning.
* Host changes must be validated and recoverable before the running Collector is
  replaced.
* No owner endpoint, Collector statement, launcher, or state convention is
  distributed to template/plugin consumers.

## Considered Options

* Keep Claude direct and rely on provider-specific OTLP translation.
* Join `target_info` to token series in every Grafana query.
* Route local metrics through Alloy and normalize there.
* Install the measurement integration with every agent-process adoption.

## Decision Outcome

Use a root-only owner launcher to create a stable repository/task/attempt tuple
before starting the selected local agent. Route Claude **metrics only** through
the existing local OTLP/HTTP receiver; Claude logs keep their direct Grafana
route. Codex continues through that receiver.

Alloy's standard `otelcol.processor.transform`, in datapoint context, promotes
Claude's independent resource attributes to:

* `vcs.repository.name`
* `task_id`
* `attempt_id`

Codex invocations carry the bounded owner-local scalar
`cpt|<project>|<task>|<attempt>`. The transform recognizes the anchored shape and
uses OTTL `Split` to create the same three datapoint attributes. Empty components
and the delimiter are rejected before launch. A legacy scalar remains a
project-only value. Missing or malformed task state becomes `unassigned`; a
malformed packed value also carries an attribution error marker.

Attempt starts are append-only under
`%LOCALAPPDATA%\agent-process\telemetry\attempts.jsonl`. The repository and issue
jointly identify reuse. GitHub PR timestamps supply outcomes; an earlier attempt
without a PR is superseded only when a later attempt starts.

The Claude settings layer also selects the metrics exporter
(`CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_METRICS_EXPORTER`,
`OTEL_EXPORTER_OTLP_METRICS_PROTOCOL`): a shell without the owner's `OTEL_*`
variables started Claude with zero metric readers and the measured launch
exported nothing with exit code 0. The launch must not depend on the caller's
shell for the very thing it exists to guarantee.

The launcher, tests, this ADR, and the measurement setup are root-only. No file
or setting from this decision is rendered into a consumer or installed by the
Claude plugin.

### Amendment: the Collector also narrows the Codex metric set

The original boundary was "adding attributes is the only mutation". The live
check showed that this is insufficient on the owner's Grafana Cloud stack:
Codex exports roughly two hundred metric names, most of them histograms, and a
single app-server session put ~14 800 `codex_*` series into the tenant, whose
`max_global_series_per_user` is 15 000. At the limit every new label set —
including every task-labelled series — was discarded with
`per_user_series_limit`, silently and with HTTP 200.

An `otelcol.processor.filter` therefore sits between the receiver and the
transform and drops every `codex*` metric except `codex.turn.token_usage`,
`codex.turn.e2e_duration_ms`, `codex.conversation.turn_count`, and
`codex.process.start`. Claude names are untouched. The doctor command treats the
filter expression as required. Names, temporality, `job`, `instance`, and the
exporter chain stay unchanged for what passes.

### Host change and rollback

The active Alloy file is backed up before replacement. A candidate must pass the
installed `alloy.exe validate` command. Alloy restarts with the exact existing
arguments in a hidden window, and the local listener is checked. A failed start
restores the prior file and user metrics endpoint, restarts the prior process,
and exits non-zero. The amendment above was installed the same way
(`config.alloy.issue-101.prefilter` backup, `validate`, restart through the
owner's `run-alloy.ps1`); a debugging `otelcol.exporter.debug` from the probe
session was removed in that restart.

### Cut-over

Historical series are not relabelled. The cut-over is the timestamp of the first
normal Claude and Codex token series observed in Grafana with matching project,
task, and attempt labels. Until that live check passes, the implementation is not
ready for a PR.

### Consequences

* Good, because the Collector is the single normalization point for both local
  carriers and dashboard queries use one label contract.
* Good, because bypasses are measurable contamination rather than silent cost
  assignment.
* Good, because the owner-only boundary avoids imposing a private measurement
  system on adopters.
* Bad, because Codex's first-party configuration cannot express independent
  values, so the owner must maintain a small private scalar codec.
* Bad, because every measured agent process must be freshly launched through the
  wrapper; an already-running IDE/app session cannot be attributed retroactively.
* Bad, because the working measurement depends on owner host state outside Git.
  The doctor command, sanitized evidence, validator, backup, and rollback make
  that dependency visible but cannot make it repository-managed.

## Confirmation

Unit tests cover identity, both carrier encodings, cleanup, attempt outcomes,
host diagnostics, and template exclusion. The installed Alloy validates the
candidate. Live evidence under ignored `evidence/issue-101/` records both
task-labelled routes, unassigned controls, preserved Claude Loki metadata, and
the cut-over time without credentials or prompts.
