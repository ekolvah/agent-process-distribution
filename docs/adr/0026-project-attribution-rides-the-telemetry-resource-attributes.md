---
status: "accepted"
date: 2026-09-12
decision-makers: repository owner
consulted: —
informed: —
---

# Project attribution rides the agent telemetry's resource attributes

## Context and Problem Statement

Token usage from every agent CLI on this machine arrives in one Grafana Cloud
tenant under `job="claude-code"` and `job="codex_*"`, with nothing on the series
saying which repository the tokens were spent on. Several repositories share the
tenant, so every accumulated number is a blend, and the A/B that the
token-efficiency work depends on cannot be run against a blended series.

The question this record answers is **where the project identity is attached**:
in the agent, in the collector, or at query time.

Everything below was settled by observation before the repository change (#97),
not by reading vendor documentation. That distinction is load-bearing here: two
earlier drafts of this work were built on documented behaviour that did not hold
on the installed versions.

## Decision Drivers

* The A/B needs a **per-project filter on the data series**, not on `target_info`.
* The 698 series already accumulated under `job="claude-code"` must not be
  orphaned by a change that alters `job` or `instance`.
* Whatever carries the project must also carry a later per-task attribute
  without being rewritten (#101).
* Host-side configuration is not inheritable by a consumer of this template, so
  as little as possible should live there.
* An attribution that can silently be wrong is worse than one that is visibly
  absent.

## Considered Options

* **(A) Query-time join against `target_info`.**
* **(B) Identifying resource attributes — `service.namespace`, `service.instance.id`.**
* **(C) Non-identifying resource attributes set by the agent, carried to the datapoints.**
* **(D) A collector-side transform promoting a resource attribute onto the datapoints.**

## Decision Outcome

Chosen option: **(C) for the Claude route, (D) for the Codex route**, because the
two routes leave the machine by different paths and only one of them can attach
the attribute itself.

`.claude/settings.json` sets `OTEL_RESOURCE_ATTRIBUTES` to a comma-joined list of
two documented OpenTelemetry registry attributes:

```
vcs.repository.name=<owner>/<repository>,vcs.repository.url.full=https://github.com/<owner>/<repository>
```

The template renders both from the Copier answers, so an adoption gets its own
value. `github_repository` (`owner/repository`) is preferred over `repo_name`
because it is globally unique; `repo_name` is the fallback, and two adopters
sharing a bare name would blend exactly as they do today. The URL pair is omitted
when `github_repository` is unanswered rather than guessed.

Codex has no equivalent variable, and its per-invocation
`-c otel.environment=<value>` override lands on the resource only. Alloy — which
is in the Codex export path and not in the Claude one — copies that resource
attribute onto every Codex datapoint as `vcs.repository.name`, so both routes end
up carrying the same label.

### Consequences

* Good, because the filter is one label name across both routes, and `job` and
  `instance` are untouched, so nothing already collected is orphaned.
* Good, because the carrier is a list from the first commit, so the planned
  per-task attribute appends to the same variable without a format change
  (#101).
* Good, because the attribute keys are documented registry attributes rather
  than invented ones, so a later reader can look them up.
* Bad, because a settings-level `OTEL_RESOURCE_ATTRIBUTES` **replaces** an
  adopter's own value of that variable rather than merging with it — observed,
  not inferred. An adopter who already sets it loses their attributes on the next
  render unless they fold their pairs into the rendered value.
* Bad, because an adoption without the Claude adapter gets no attribution at all:
  `claude_adapter_installed` defaults to `false`, so the conditional directory
  renders nothing. The safe direction — such a tree reads as "not this project"
  rather than being folded in — but it is a real gap, named in the measurement
  setup document rather than left to be discovered.
* Bad, because the Codex half depends on host state outside this repository, and
  on a per-invocation flag nothing enforces (see below).

### The Codex attribution condition

The host-wide `[otel] environment` was corrected from a value naming a different
repository to `unattributed`, so an un-flagged Codex run is visibly unattributed
rather than silently charged to the wrong project. Attribution requires
`-c otel.environment=<owner>/<repository>` at launch.

Nothing enforces that flag: the role catalogue makes the carrier a per-run human
choice (`carrier_selection: "run_route"`), and `implementer` and `fixer` default
to Codex — the two largest token consumers.

**The audit surface the issue named does not exist.** `Agent handoff` records
`planner:`, `validation:`, `next role:` and `handoff:` — `handoff_gaps` in
`validate_issue_sections.py` requires exactly those four and nothing else — so it
names the planner, never the carrier that implemented or fixed. The PR report has
no carrier field either. An issue's provenance blocks therefore cannot answer
"which carrier spent these tokens", and a condition written against them would be
unenforceable in a way that looks enforced.

The surface that does exist is the telemetry itself, and it is better because it
is an observation rather than a declaration: an un-flagged Codex run lands on
`vcs_repository_name="unattributed"`, so a non-zero `unattributed` count inside a
measured window is a **visible anomaly** saying some role ran outside the
attribution, rather than a silent blend into the arm. The measurement issue (#99)
records that as the condition: a measured window with Codex traffic under
`unattributed` is not a valid arm until that traffic is either attributed or
explained.

### The data already collected

Everything gathered before this change is unattributed and blended across every
repository sharing the tenant. It is **kept with a caveat rather than
re-measured**: re-measurement is impossible — the identity was never recorded, so
there is nothing to recover it from — and discarding it would lose the only
evidence that the exporters work at all. The consequence is that the A/B's
baseline arm must be measured **after** this change, not read off the existing
series, and the measurement issue (#99) carries that as a precondition rather
than inheriting a blended number silently.

### Confirmation

* `template_drift.py` passes with the root `.claude/settings.json` equal to its
  render, so the template and the self-applied root cannot diverge.
* Two render tests in `tests/publisher/test_project_bootstrap_template.py` assert
  that the rendered value follows the answered repository and that this
  repository's own name never leaks into another adoption's render.
* `TestTelemetryAttribution` asserts the committed carrier stays a multi-pair
  `key=value` list whose project pair matches the Copier answers.
* The live half is deliberately **not** under test: no test asserts that a
  running session emits the attribute, because that crosses a process boundary
  into a third-party exporter. It is covered instead by a one-shot observation
  with captured evidence — the same convention already used for branch
  protection and test-suite ownership.

## Pros and Cons of the Options

### (A) Query-time join against `target_info`

* Bad, because it does not work here at all. `job` varies by **invocation mode**
  for Codex (`codex-app-server`, `codex_cli_rs`, `codex_exec`), not by project,
  and `instance` is absent from every series in the tenant — so for one `job` the
  `env` value flips per invocation and the join is ambiguous.
* Bad, because every dashboard panel would have to carry the join.

### (B) Identifying resource attributes

* Bad, because the OTLP-to-Prometheus translation folds `service.namespace` and
  `service.instance.id` into `job` and `instance`, which would orphan the series
  already accumulated under `job="claude-code"`.

### (C) Non-identifying resource attributes set by the agent

* Good, because Claude Code attaches `OTEL_RESOURCE_ATTRIBUTES` values to **every
  metric datapoint**, not only to `target_info` — observed across all four `type`
  values, with the dotted keys surviving as `vcs_repository_name` and
  `vcs_repository_url_full`.
* Good, because it needs no collector and no host state beyond the transport
  variables that already exist.
* Neutral, because the pairs reach Loki as per-entry structured metadata rather
  than as indexed stream labels — filterable, but a query must select on
  `service_name` first. Handed to the measurement issue, which reads Loki
  (#99).
* Bad, because Codex cannot do it.

### (D) A collector-side transform

* Good, because it is the only remaining route to an attributed Codex series, and
  it was authorised by the owner on 2026-09-12 for exactly this purpose.
* Neutral, because it costs one processor in a config that already had three.
* Bad, because it is host state a template consumer cannot inherit, and it has to
  be maintained by hand alongside the collector.

## More Information

The observation records — the four pre-change checks and the post-change
verification of both routes — are captured under `evidence/issue-97/`, which is
working-tree-only. The redaction-safe summary of what they establish is in
[the measurement setup document](../telemetry-measurement-setup.md), which is the
durable home for the setup itself: which variables, which collector, which
dashboards, and which label carries what.
