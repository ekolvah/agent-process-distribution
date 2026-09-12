# Agent telemetry measurement setup

**Question this document answers:** how agent token usage is exported, where it
lands, and which label identifies the project it was spent on.

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

The two routes take different paths out of the machine, and that is what makes a
collector-side fix possible for one of them and unnecessary for the other:

- **Claude Code** exports straight to Grafana Cloud over 443. It never touches
  the collector, and it does not need to — its attributes are already on the
  datapoints.
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
