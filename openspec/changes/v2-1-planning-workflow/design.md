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
- **Approval = the person runs `/opsx:apply <change>`.** OpenSpec's planning boundary stops
  `propose` before code; nothing implements until that command. No approval state file.
- **Delivery steps are tasks, not a wrapper skill.** The `tasks` rule puts the GitHub steps
  (issue, branch, status … `ci_check`, PR, `wait_for_pr` loop, `finish_change`) into every
  `tasks.md`, so the unmodified `openspec-apply-change` — the
  command the generated propose prompt hands off to — runs them. Alternative: an
  `implement-change` wrapper — a second entry point the OpenSpec prompts do not know, so it
  gets bypassed. A re-run on an open PR continues at the first unchecked task.
- **`finish_change` closes the loop itself.** The apply skill marks a task after running it,
  and `openspec archive` moves `tasks.md`; so the last task is one script that marks its own
  box first, then archives, commits, pushes and waits — nothing is left to edit after the
  archive commit.

## Risks / Trade-offs

- Forked schema must be re-forked on OpenSpec schema changes; `openspec schema validate` in
  CI catches drift.
- Changes created before the fork (`v2-2` … `v2-6`) lack `architect-review.md`; task 1.4
  writes it, otherwise the apply skill reports them blocked.
- Codex has no Stop hook; `wait_for_pr` is the only end guard.
- A planner may drop a delivery task; the architect review and the PR reviewer read
  `tasks.md` against the template.
