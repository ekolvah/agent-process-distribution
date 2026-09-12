# Agent telemetry measurement setup

**Question this document answers:** how agent token usage is exported, where it
lands, which label identifies the project it was spent on, and which labels
identify the task and delivery attempt.

This is the owner-side setup that the token-efficiency measurement depends on.
Until this file existed, the whole configuration lived on one machine and in one
session transcript; a single line in an ADR was the only mention of telemetry in
the tree. Every claim below was observed, not read out of vendor documentation —
the observations were captured before the repository change that this document
accompanies (#97), and the two that contradict the documentation are marked.

## What exports what

| Route | Switch | Metric | Token categories |
| --- | --- | --- | --- |
| Claude Code | `CLAUDE_CODE_ENABLE_TELEMETRY=1` plus the `OTEL_EXPORTER_OTLP_*` transport variables | `claude_code_token_usage_tokens_total` | `type` ∈ `input` / `output` / `cacheRead` / `cacheCreation` |
| Codex | the `[otel]` table in `~/.codex/config.toml` | `codex_turn_token_usage_sum` | `token_type` ∈ `input` / `cached_input` / `output` / `reasoning_output` / `total` |

Both push OTLP to Grafana Cloud: metrics to the Prometheus datasource, logs to
the Loki datasource. The transport variables (endpoint, protocol, headers) and
the service-account token live in the owner's Windows User-scope environment and
are deliberately absent from this repository — nothing here reads them, and
nothing here should print them.

Dashboards are referred to by UID rather than by URL, for the same reason:
`agwhkq` and `axwvz9`.

## Which label carries the project

`.claude/settings.json` sets `OTEL_RESOURCE_ATTRIBUTES` to a comma-joined
`key=value` list:

```
vcs.repository.name=<owner>/<repository>,vcs.repository.url.full=https://github.com/<owner>/<repository>
```

The template renders both pairs from the Copier answers, so a new adoption
inherits its own value rather than this repository's. The URL pair is omitted
when `github_repository` is left blank — there is no canonical URL to state, and
a guessed one is worse than an absent one.

`vcs.repository.name` and `vcs.repository.url.full` are documented OpenTelemetry
registry attributes, not invented keys. The identifying attributes
`service.namespace` and `service.instance.id` were rejected on purpose: the
OTLP-to-Prometheus translation folds them into `job` and `instance`, which would
orphan the series already accumulated under `job="claude-code"`.

**Observed, not assumed:** the dotted keys survive the translation as
`vcs_repository_name` and `vcs_repository_url_full`, and they arrive **as labels
on the token series**, not only on `target_info`. All four `type` values carry
them. A Prometheus query filtered on this project's value returns the token
series; the same query with another project's value returns nothing.

In Loki the pairs ride as **per-entry structured metadata**, not as indexed
stream labels — `service_name` is the only indexed label — so a Loki query must
select on `service_name` first and filter on the project afterwards.

The carrier is a **list from the first commit** on purpose. `OTEL_RESOURCE_ATTRIBUTES`
is one string with no merge semantics, and a later per-task attribute (#101) has
to be appended to the same variable; a single-pair carrier would have to be
rewritten to accept it.

## Two failure conditions that are usually silent

The vendor documentation names two conditions under which a settings `env` block
does not take effect. Both were exercised on Claude Code 2.1.265 / 2.1.268, and
**neither reproduced**:

- **Relaunch.** A session that was already running when the settings file was
  written picked up the new value, and picked up a second value after a second
  write — two distinct label values matching the two writes, with no relaunch.
- **Folder trust.** A settings `env` block in a directory Claude Code had never
  run in before was applied by a headless run. The interactive first-run trust
  prompt was not exercised, so that half remains untested.

Record both as *not reproduced here*, not as *does not apply*. A reader on a
different version must check rather than rely on either direction. The direction
that matters for a mistake is cheap to check: query the token series for
`vcs_repository_name` and see whether the current project's value is present.

**Precedence is observed, and it is the sharp edge for an adopter.** With a
settings `env` value and an inherited process-environment value of the same
variable set at the same time, the **settings value wins outright**: the
process-environment value appears nowhere in the telemetry. A settings-level
`OTEL_RESOURCE_ATTRIBUTES` therefore *replaces* an adopter's own resource-attribute
set rather than adding to it. An adopter who already sets that variable loses
their attributes silently on the next render, and must fold their own pairs into
the rendered value by hand.

## What a render does not get

`claude_adapter_installed` defaults to `false`. A default or Codex-only adoption
renders no `.claude/` directory at all and therefore gets **no attribution from
the template**. That is the safe direction — an unlabelled tree reads on the
dashboard as "not this project" rather than being silently folded in — but it is
not a no-op: such an adoption has to carry the attribute some other way before
its numbers can be compared with anything.

The same applies to trees in this repository's own neighbourhood that have a
`.claude/settings.json` without Copier answers. They get the `env` key by hand or
they stay unlabelled.

## The Codex route needs the collector

Codex has no equivalent of `OTEL_RESOURCE_ATTRIBUTES`. It offers one global
`[otel]` table in `~/.codex/config.toml` and a per-invocation
`-c otel.environment=<value>` override; `[projects.'<path>']` accepts
`trust_level` only, so there is no per-directory `[otel]` table.

That override alone does **not** attribute the data series. It lands on the
resource, which the translation parks in `target_info`, and `target_info` cannot
be joined back onto `codex_turn_token_usage_sum` here: `job` varies by invocation
mode (`codex-app-server`, `codex_cli_rs`, `codex_exec`) rather than by project,
and `instance` is absent from every series in the tenant, so for one `job` the
value flips per invocation and the join is ambiguous.

The two routes took different paths out of the machine when project attribution
landed (#97), and that is what made a collector-side fix possible for one of
them and unnecessary for the other:

- **Claude Code** exported straight to Grafana Cloud over 443. Its project
  attributes were already on the datapoints. With per-task attribution its
  *metrics* go through the collector too — see
  [Per-task attribution](#per-task-attribution) — while its logs keep the
  direct route.
- **Codex** exports to a local Grafana Alloy instance on `127.0.0.1:4318`, which
  forwards to the same Grafana Cloud tenant.

So Alloy carries an `otelcol.processor.transform` that copies the `env` resource
attribute onto every Codex datapoint as `vcs.repository.name`. Both routes then
carry the same label name and one dashboard filter covers both. **Observed:**
after the transform, `codex_turn_token_usage_sum` and
`codex_turn_token_usage_count` carry `vcs_repository_name` with this repository's
value.

The host-wide `[otel] environment` is `unattributed`, so a Codex run launched
without the override lands under `unattributed` rather than being charged to
whatever project was named last. Attribution therefore still depends on a
per-invocation flag that nothing enforces:

```
codex -c otel.environment=<owner>/<repository>
```

That residual gap is not a documentation problem; it is a measurement condition,
and it is auditable: Codex traffic sitting under `vcs_repository_name="unattributed"`
inside a measured window means some role ran outside the attribution. The
reasoning and the decision are in
[ADR 0026](adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md).

The collector configuration lives on the owner's machine, outside this
repository, for the same reason the transport variables do: it is host state, not
project state, and a consumer of this template must not inherit it. Changing it
is an owner decision each time.

## Per-task attribution

A session is neither an issue nor a delivery attempt, so `session_id` cannot
answer "what did this task cost". Two more labels ride next to
`vcs_repository_name` on every measured token series: `task_id` (`issue-N`) and
`attempt_id` (`issue-N-<uuid>`). The decision and its boundaries are in
[ADR 0027](adr/0027-owner-host-normalizes-per-task-agent-telemetry.md).

**Owner-only.** Everything in this section is root-only host state:
`scripts/owner_task_attribution.py`, its test, the ADR, the Alloy transform, the
User-scope metrics endpoint, and the attempt ledger. None of it is rendered by
Copier or installed by the Claude plugin; `template-drift-allowlist.yml` declares
the files and `test_owner_task_attribution_is_root_only` proves the absence.

### Launching a measured task

```
python scripts/owner_task_attribution.py launch --issue N --carrier claude [--new-attempt] -- claude
python scripts/owner_task_attribution.py launch --issue N --carrier codex  [--new-attempt] -- codex
```

The launcher derives the project from `gh repo view` in the current checkout,
takes the issue from `--issue` (or, when omitted, from the branch through
`open_pr.ISSUE_BRANCH_RE`; a branch that names no issue launches as
`unassigned`), and creates or reuses one attempt id before the agent process
starts. Planner, implementer, resume, and fixer launches for the same
repository+issue reuse the latest attempt; `--new-attempt` opens another.
Switching issues is a new launch. An agent that is already running — an IDE or
app session — cannot be attributed retroactively.

- **Claude** gets one complete settings layer written to a temporary file under
  the ledger directory and passed as `--settings <path>`. It carries the whole
  `OTEL_RESOURCE_ATTRIBUTES` value (project, task, attempt),
  `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`, and the metrics switch itself
  (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_METRICS_EXPORTER=otlp`,
  `OTEL_EXPORTER_OTLP_METRICS_PROTOCOL=http/protobuf`). **Observed**: a shell
  without the User-scope `OTEL_*` variables started Claude with zero metric
  readers (`getOtlpReaders: types=[]` in the debug log) and the measured launch
  exported nothing, with exit code 0; the layer now selects the exporter so the
  launch does not depend on the caller's shell. The file is removed in a
  `finally` path; the repository `.claude/settings.json` is never touched. A
  command that already contains `--settings` is refused rather than merged.
- **Codex** gets `-c otel.environment=cpt|<project>|<task>|<attempt>`. The
  encoder rejects the `|` delimiter and empty components; the decoder is the
  same contract read back, so the launcher can never emit a value the collector
  would not recognize.

### What the collector does with it

Claude metrics now go to `http://127.0.0.1:4318/v1/metrics` through the
User-scope `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`; the generic
`OTEL_EXPORTER_OTLP_ENDPOINT` remains and still carries Claude logs directly to
Grafana Cloud. Codex keeps sending to the same receiver.

The receiver feeds an `otelcol.processor.filter "codex_cardinality"` first. It
drops every metric whose name starts with `codex` except
`codex.turn.token_usage`, `codex.turn.e2e_duration_ms`,
`codex.conversation.turn_count`, and `codex.process.start` (dot or underscore
spelling); Claude names pass untouched. The reason is the tenant series limit
described [below](#the-tenant-series-limit-is-a-precondition). `doctor` fails
when the filter expression is absent.

The datapoint-context `otelcol.processor.transform` then promotes, in order:

1. Claude resource `vcs.repository.name`, `task_id`, `attempt_id` → datapoint
   attributes of the same names.
2. A Codex `env` that matches the anchored `^cpt|…|…|…$` shape → the same three
   attributes through OTTL `Split`.
3. A Codex `env` without the `cpt|` prefix → project-only, the pre-existing
   behaviour (#97).
4. Anything else: `task_id="unassigned"`, `attempt_id="unassigned"`; a `cpt|`
   value that fails the shape also gets `vcs.repository.name="unattributed"` and
   `attribution_error="malformed"`.

Adding attributes is the only mutation. Metric names, temporality, `job`,
`instance`, the delta-to-cumulative and batch stages, and the exporter chain are
unchanged. **Observed** on the installed Alloy 1.18.1 with six sanitized OTLP
probes (full Claude, bypass Claude, packed Codex, legacy Codex, host-default
`unattributed`, malformed packed): each produced exactly the datapoint attributes
listed above.

`python scripts/owner_task_attribution.py doctor` checks that the active config
contains the cardinality filter and every promotion rule, that the User-scope
metrics endpoint is the local receiver, and that the listener answers. It
prints no endpoint credentials.

### Unassigned is the audit signal

A measured window is valid only when it contains no `task_id="unassigned"`
traffic for the project. Unassigned traffic means some role ran outside the
launcher — a plain `claude` or `codex` start, an IDE session, or a malformed
Codex value — and the token-efficiency measurement rejects such a window rather
than guessing (#99). A bypass never inherits the previous task's labels.

### Attempts and outcomes

The ledger is append-only JSON lines at
`%LOCALAPPDATA%\agent-process\telemetry\attempts.jsonl`, outside every
worktree. `python scripts/owner_task_attribution.py outcomes` joins each start
window with the live PRs whose head branch names the same issue and reports
`merged`, `closed_unmerged`, `open`, or `superseded_without_pr` (an earlier
attempt without a PR, superseded only by a later start for the same
repository+issue). Malformed records and overlapping windows fail non-zero.

### Host change, rollback, and cut-over

Before the transform was extended the previous config was copied to
`~/.config/alloy/config.alloy.issue-101.prechange`, the candidate passed
`alloy.exe validate --stability.level=experimental`, and Alloy was restarted
with its existing arguments. The cardinality filter went in the same way with
the backup `~/.config/alloy/config.alloy.issue-101.prefilter`; that restart also
removed a debugging `otelcol.exporter.debug` left from the probe session and
went through `~/.config/alloy/run-alloy.ps1`, so stdout/stderr are redirected
again. Rollback is the reverse: restore the wanted backup, unset the User-scope
`OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`, restart Alloy through `run-alloy.ps1`, and
confirm the listener on `127.0.0.1:4318`.

Historical series are not relabelled. The cut-over is the first normal,
long-lived Claude and Codex launch through the wrapper whose token series carry
matching project/task/attempt labels in Grafana; the ADR records that timestamp
once observed.

### The tenant series limit is a precondition

Grafana Cloud's `max_global_series_per_user` for this stack is 15 000. Codex
exports roughly two hundred metric names, most of them histograms, and a single
app-server session put ~14 800 `codex_*` series into the head block on
2026-09-12. While `grafanacloud_instance_memory_series` sits at the limit every
*new* label set — including every task-labelled series — is discarded with
`per_user_series_limit`, silently and with HTTP 200. The transform is not the
failing part; the tenant is. Check
`grafanacloud_instance_samples_discarded_per_second{reason="per_user_series_limit"}`
in the `grafanacloud-usage` datasource before reading any live result as
evidence.

The `codex_cardinality` filter is the standing mitigation: only the four
turn-level Codex names the measurement reads reach the tenant. **Observed** on
2026-09-12 after the restart: `grafanacloud_instance_memory_series` fell from
15 000 to 2 311 and the discard rate to zero; a `codex_turn_token_usage` probe
with a packed `env` arrived with all three labels, while
`codex_sse_event_duration_ms` and `codex_websocket_request_duration_ms` probes
through the same receiver produced no series. This narrows the Codex metric set
the collector forwards, which the ADR records as an amendment to its original
"add attributes only" boundary.
