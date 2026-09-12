# Telemetry

**Question this document answers:** how token efficiency of the process is measured, which
metrics compare two versions of the process, and where that measurement lives.

Status: draft

## Requirements

- **TELE-1** (MUST) Measurement is an **optional owner-side module**, outside the process
  core: nothing in the plugin, the skills or the reusable workflows depends on it or ships
  it (ADR 0027 boundary).
- **TELE-2** (MUST) Both agents export OTLP metrics through one local collector that
  attaches project, task and attempt labels; project identity rides the resource
  attributes (ADR 0026), task and attempt identity are created by the launcher before the
  agent starts (ADR 0027).
- **TELE-3** (MUST) Process versions are compared on per-PR metrics, never on raw token
  sums: tokens per merged PR by role (plan / implement / fix), review rounds per PR, share
  of PRs merged without a fixer commit, agent turns per issue.
- **TELE-4** (MUST) Every measured task records the process version tag it ran under, so
  an A/B between v1 and v2 is a filter, not an archaeology exercise.
- **TELE-5** (SHOULD) A launch that bypasses the launcher is labelled `unassigned` and is
  the audit signal, never charged to the previous task.

## Rationale

The whole redesign claims to cut tokens and rework; without TELE-3 that claim is
unfalsifiable. Raw token totals grow with the number of tasks and say nothing about
efficiency, which is why the unit is the merged PR. The owner's host setup is documented in
[`telemetry-measurement-setup.md`](../telemetry-measurement-setup.md); this spec only
fixes what the measurement must be able to answer.

## Non-goals

- Shipping telemetry configuration to consumers.
- Session-level accounting (one session spans several issues; one issue spans several
  sessions).

## Open questions

- The minimum number of comparable tasks per version before a difference in TELE-3
  metrics is treated as a signal; settled by the first v1-vs-v2 comparison.

## Traceability

- ADR 0026, 0027 — kept as the owner-side design.
- The measurement work this spec generalizes (#97, #99, #101).
- `docs/telemetry-measurement-setup.md`, `scripts/owner_task_attribution.py`.
