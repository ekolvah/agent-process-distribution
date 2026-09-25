# Repository agent guidance

The process is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec) and is the
source of truth: `openspec/specs/` holds what is implemented, `openspec/changes/` what is
pending (the tracking issue #107 lists the v2 changes), `openspec/config.yaml` the repository
context, and [`skills/agent-process/SKILL.md`](skills/agent-process/SKILL.md) the portable
procedure. A PR that changes behaviour carries its change's spec delta
(`openspec validate --strict`). Roles are interchangeable: do not assume that the current
Claude or Codex adapter is the only permitted executor.

## Codex adapter

- A repository must be installed once before its first delivery
  ([Install](skills/agent-process/SKILL.md#install)). Until then, `start_change.py` refuses
  to create a branch.
- Codex loads `.codex/hooks.json` only for a trusted project;
  `python .agent-process/scripts/check_codex_project_trust.py` checks that trust.
- Follow the [tasks](skills/agent-process/SKILL.md#tasks) and [delivery](skills/agent-process/SKILL.md#delivery)
  of the skill. They are the sole
  source of task gates, commands, and status transitions; this file does not restate them.
- Use `$openspec-propose` for the Codex planner entry point and
  `$openspec-apply-change` for the Codex implementer entry point. The project context and
  shared-skill pointers they follow are in `openspec/config.yaml`; the architect review is written as
  `architect-review.json` by the planner as a self-review in Codex; they do not
  replace any gate of the delivery flow.

## Repository conventions

- <!-- List this project's own recurring environment pitfalls here (shell,
  OS, subprocess encoding, path quirks) — start from the target repository's
  actual toolchain, not this template's origin project. -->
- Capture Python subprocess output with `encoding="utf-8"`; do not turn a
  `None` stdout or stderr into an empty string.
- Keep a PR to one logical unit. Update planned docs and ADRs, or explicitly
  record why they do not apply.
- Follow [Principle V](.agent-process/docs/architecture/principles.md#v-root-cause-before-fix):
  instrument before patching, and observe the live external system when a plan
  depends on how that system is read or classified.
- Never bypass hooks, push directly to `main`, force-push, hard-reset,
  force-delete a branch, or self-merge. The repository hook is supplementary;
  GitHub branch protection remains the final barrier.

## Code review

Codex code review is the primary carrier: the PR author starts it with
`@codex review`, and workflows validate its standard GitHub review on the
current head. Claude remains the fallback carrier only when Codex leaves no
valid current-head evidence. Their reporting contract is
[REVIEW_CONTRACT.md](.agent-process/REVIEW_CONTRACT.md). The gate's parser and enforcement code
come from the default branch, but either review is evidence, not a substitute
for the platform workflow-definition trust anchor.
