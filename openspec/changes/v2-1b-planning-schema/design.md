## Context

Umbrella design: `v2-0-decision-record/design.md`. Verified on OpenSpec 1.13.0:

- `openspec schema fork spec-driven <name>` copies the schema and its templates under
  `openspec/schemas/<name>/`; `config.yaml` `schema:` selects it for new changes; each change
  records its schema in `.openspec.yaml`, so the changes of part 1 stay `spec-driven`.
- `config.yaml` `rules:` per artifact are injected into `openspec instructions <artifact>`
  as `rules`; plain scalars with `: ` break YAML, so every rule is a `>-` block scalar.
- `openspec instructions proposal --json` is 6 829 bytes with the current `context`
  (1 273 bytes); appending the whole `principles.md` gives 20 695 (cap 51 200). The context
  stays minimal: a pointer to the principles.
- `agents/architect-reviewer.md` is a plugin agent (`.claude-plugin/plugin.json`); in this
  repository's own session it is not installed, so the review is a self-review here.

## Goals / Non-Goals

**Goals:** planning and implementation run on the unmodified OpenSpec skills; every project
specific is one rule in one file. **Non-Goals:** removing v1 (part 3), review and state
rework (`v2-4`), `init` (`v2-2`), a Codex end-to-end run (observed at the apply of `v2-2`).

## Decisions

- **The change directory is the plan; the issue is the tracker.** `openspec/changes/<name>/`
  holds proposal, deltas, design, architect review, tasks. The issue holds title, change name
  and priority and is the Project item. Alternative: issue body as the plan (v1) — no
  validator, no archive, no living spec.
- **Project specifics are configuration, not a second skill.** Alternative: a bespoke
  `plan-issue` skill — re-implements the propose loop once, worse.
- **Approval = the person runs `/opsx:apply <change>`.** OpenSpec's planning boundary stops
  `propose` before code. No approval state file; a marker only after an observed unapproved
  apply.
- **Delivery steps are tasks, not a wrapper skill.** The `tasks` rule puts the GitHub steps
  into every `tasks.md`, so the unmodified `openspec-apply-change` runs them. A re-run on an
  open PR continues at the first unchecked task. The rule names the tracking issue as a plain
  reference in the PR body, not `Closes`: the branch from `gh issue develop -c` closes the
  issue on merge, and a `Closes` line would mask whether that link works (observed on the
  consumer migration, #117).
- **Review budget: three rounds**, prose; a counter after an observed overrun.
- **The schema is forked, not patched.** `openspec schema validate agent-process` in
  `test_openspec_valid.py` catches drift from upstream `spec-driven`.

## Risks / Trade-offs

- [A planner drops a delivery task] → the architect review and the PR reviewer read
  `tasks.md` against the `tasks` rule; a `check_tasks` script only after an observed drop.
- [Two routes during the transition] → part 3 follows immediately; `AGENTS.md` and
  `workflow.md` change there, in one docs PR.

## Migration Plan

One PR on top of part 1; the change archives through `finish_change`; the person merges.
Rollback: revert the PR — `config.yaml` returns to `spec-driven`.
