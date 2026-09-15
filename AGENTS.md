# Repository agent guidance

Use [the agent development process](.agent-process/docs/architecture/agent-process.md) as the
source of truth. Roles are interchangeable: do not assume that the current
Claude or Codex adapter is the only permitted executor.

The **target** process is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec):
`openspec/specs/` holds what is implemented, `openspec/changes/` what is pending (the
tracking issue #107 lists the v2 changes), `openspec/config.yaml` the conventions. A PR that
changes target behaviour carries its change's spec delta (`openspec validate --strict`); a
PR that only touches a v1 mechanism the target drops does not. Until v2 lands the document
above stays the enforced contract.

## Codex adapter

- A repository must be activated once before its first delivery. Follow
  [the installation guide](.agent-process/docs/architecture/agent-process-installation.md),
  then commit its generated `.agent-process/scripts/project_settings.py`. Until activation
  succeeds, `issue_branch.py` refuses to create a branch.
- Follow the canonical [per-issue delivery flow](.agent-process/docs/architecture/agent-process.md#deterministic-delivery-flow).
  That document is the sole source of task gates, commands, and status
  transitions; this file does not restate them.
- Use `$openspec-propose` for the Codex planner entry point and
  `$openspec-apply-change` for the Codex implementer entry point. The project rules
  they follow are in `openspec/config.yaml`; the architect review is written as
  `architect-review.md` by the planner as a self-review in Codex; they do not
  replace any gate in that document.
- The advisory control plane (`.agent-process/scripts/agent_orchestrator.py` plus
  `.agents/orchestration/roles.yaml`) reports evidence-based routing and budget
  escalation. It never authorizes bypassing its required delivery gates.

## Repository conventions

- <!-- List this project's own recurring environment pitfalls here (shell,
  OS, subprocess encoding, path quirks) — start from the target repository's
  actual toolchain, not this template's origin project. -->
- Test runner: `python -m pytest --junitxml=.pytest-report.xml <paths>`; the report path is
  `.pytest-report.xml` (untracked). The RED gate reads it:
  `python .agent-process/scripts/check_red.py --report .pytest-report.xml <node ids>`.
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
