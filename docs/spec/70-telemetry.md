# Telemetry

**Question this document answers:** how token efficiency of the process is measured, which
metrics compare two versions of the process, and where that measurement lives.

Status: draft

## Requirements

- **TELE-1** (MUST) Measurement is an **optional owner-side module**, outside the process
  core: nothing in the plugin, the skills or the reusable workflows depends on it or ships
  it. The owner's host setup is in
  [`telemetry-measurement-setup.md`](../telemetry-measurement-setup.md).
- **TELE-2** (MUST) Both agents export OTLP metrics through one local collector that
  attaches project, task and attempt labels; project identity rides the resource
  attributes, task and attempt identity are created by the launcher before the agent
  starts.
- **TELE-3** (MUST) Process versions are compared on per-PR metrics, never on raw token
  sums: tokens per merged PR by role (plan / implement / fix), review rounds per PR, share
  of PRs merged without a fixer commit, agent turns per issue.
- **TELE-4** (MUST) Every measured task records the process version tag it ran under, so
  an A/B between v1 and v2 is a filter.
- **TELE-5** (SHOULD) A launch that bypasses the launcher is labelled `unassigned` and is
  the audit signal, never charged to the previous task.
- **TELE-6** (MUST NOT) No telemetry configuration shipped to consumers; no session-level
  accounting (one session spans several issues; one issue spans several sessions).
