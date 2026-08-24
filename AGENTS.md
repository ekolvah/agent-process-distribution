# Repository agent guidance

Use [the agent development process](docs/architecture/agent-process.md) as the
source of truth. Roles are interchangeable: do not assume that the current
Claude or Codex adapter is the only permitted executor.

## Codex adapter

- A repository must be activated once before its first delivery. Follow
  [the installation guide](docs/architecture/agent-process-installation.md),
  then commit its generated `scripts/project_settings.py`. Until activation
  succeeds, `issue_branch.py` refuses to create a branch.
- Follow the canonical [per-issue delivery flow](docs/architecture/agent-process.md#deterministic-delivery-flow).
  That document is the sole source of task gates, commands, and status
  transitions; this file does not restate them.
- Use `$plan-issue #N` for the Codex planner entry point and
  `$implement-issue #N` for the Codex implementer entry point. They execute
  the canonical role contracts; they do not replace any gate in that document.
- The advisory control plane (`scripts/agent_orchestrator.py` plus
  `.agents/orchestration/roles.yaml`) reports evidence-based routing and budget
  escalation. It never authorizes bypassing its required delivery gates.

## Repository conventions

- <!-- List this project's own recurring environment pitfalls here (shell,
  OS, subprocess encoding, path quirks) — start from the target repository's
  actual toolchain, not this template's origin project. -->
- Capture Python subprocess output with `encoding="utf-8"`; do not turn a
  `None` stdout or stderr into an empty string.
- Keep a PR to one logical unit. Update planned docs and ADRs, or explicitly
  record why they do not apply.
- Follow [Principle V](docs/architecture/principles.md#v-root-cause-before-fix):
  instrument before patching, and observe the live external system when a plan
  depends on how that system is read or classified.
- Never bypass hooks, push directly to `main`, force-push, hard-reset,
  force-delete a branch, or self-merge. The repository hook is supplementary;
  GitHub branch protection remains the final barrier.

## Code review

Codex code review is the sole carrier of the required review gate. The PR author
starts it with `@codex review`; workflows only wait for and validate the standard
GitHub review on the current head. Its reporting contract is
[REVIEW_CONTRACT.md](REVIEW_CONTRACT.md). The gate's parser and enforcement code
come from the default branch, but a Codex review is owner-requested evidence,
not a substitute for the platform workflow-definition trust anchor.
