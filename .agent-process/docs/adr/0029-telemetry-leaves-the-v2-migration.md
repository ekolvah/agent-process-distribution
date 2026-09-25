---
status: "accepted"
date: 2026-09-25
decision-makers: ekolvah
---

# Telemetry leaves the v2 migration

## Context and Problem Statement

[ADR 0027](0027-v2-standards-replace-the-bespoke-control-plane.md) makes telemetry the last
step of v2 (`v2-6`): OTLP from both agents through one collector, comparisons per merged PR,
and "the `telemetry` metrics are no worse than v1 on the same task types" as part of its
confirmation. When that step came to be planned on 2026-09-25, two facts no longer fitted it:

* The per-task backend is not decided. The Langfuse evaluation (#103) has no recorded
  outcome, and it may replace the collector route that ADR 0027 names.
* v1 PRs carry no `task_id`, and a PR's time window does not separate sessions that ran in
  parallel. With v1 gone, no new v1 task runs, so "no worse than v1" has no v1 side to
  measure.

This record supersedes, in ADR 0027, the scope sentence of Decision Outcome ("delivered by
the changes `v2-1` … `v2-6`"), its telemetry bullet, the telemetry clause of Confirmation
and the telemetry item of Deletion condition. The rest of ADR 0027
stays in force, and ADR 0027 remains `accepted`.

## Considered Options

* Plan `v2-6` now on the collector route and keep the v1 comparison
* Keep `v2-6` in v2 and wait for the Langfuse evaluation before closing v2
* Move telemetry out of v2 and compare forward only

## Decision Outcome

Chosen: **move telemetry out of v2 and compare forward only.**

* v2 is `v2-0` … `v2-5`; the migration closes with the second consumer project (#117).
* Telemetry stays owner-side with project, task and attempt identity. Its backend is chosen
  by the Langfuse evaluation (#103), and the telemetry change (#116) is planned after it.
  That change takes over the task launcher of #101, which supersedes PR 104. The work is
  tracked in the process roadmap (#169).
* v2 is confirmed without a telemetry criterion. A v1-to-v2 comparison, if one is ever made,
  replays one fixed task set under both versions (#99).

### Consequences

* Good, because v2 closes on what it delivers, not on an unmade backend decision.
* Good, because the telemetry plan is written once, against the chosen backend.
* Bad, because v2 is accepted without a measured token or review-round effect.

### Deletion condition

A replay of one fixed task set under v1 and v2 shows v2 worse → the v2 decision is revisited
in a new record.

### Confirmation

Issue 107 lists step 6 as moved out and closes with step 7; `openspec/config.yaml` names
`v2-0` … `v2-5` as the v2 target.
