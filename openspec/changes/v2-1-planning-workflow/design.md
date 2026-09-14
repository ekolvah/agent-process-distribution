## Context

Umbrella design: `v2-0-decision-record/design.md`. This change replaces the planner and
implementer procedures with OpenSpec skills plus thin GitHub glue.

## Decisions

- **The change directory is the plan; the issue is the tracker.** `openspec/changes/<name>/`
  holds proposal, deltas, design, architect review, tasks. The GitHub issue holds title,
  change name and priority and is the Project item. Alternative: issue body as the plan (v1)
  — no validator, no archive, no living spec.
- **Project specifics are configuration, not a second skill.** `config.yaml` `rules:` per
  artifact are injected into `openspec instructions`; the forked schema inserts
  `architect-review` between `design` and `tasks`. Alternative: bespoke `plan-issue` skill —
  re-implements the propose loop once, worse.
- **Approval = the person runs `/implement <change>`.** OpenSpec's planning boundary stops
  `propose` before code; nothing implements until that command. No approval state file.
- **`implement-change` is a wrapper.** Pre-steps (issue, branch, status) → follow
  `openspec-apply-change` → post-steps (`ci_check`, PR, `wait_for_pr`). A re-run on an open
  PR reads unresolved threads instead of `tasks.md`.

## Risks / Trade-offs

- Forked schema must be re-forked on OpenSpec schema changes; `openspec schema validate` in
  CI catches drift.
- Codex: `$implement-change` has no Stop hook; `wait_for_pr` is the only end guard.
