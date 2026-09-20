# Repository agent guidance

Load [`skills/agent-process/SKILL.md`](skills/agent-process/SKILL.md) for the portable
planning, delivery, architect-review, and installation procedure. Use
[the architecture document](.agent-process/docs/architecture/agent-process.md) for this
publisher's operational boundary and rationale. Roles are interchangeable.

The **target** process is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec):
`openspec/specs/` holds what is implemented, `openspec/changes/` what is pending (the
tracking issue #107 lists the v2 changes), `openspec/config.yaml` the conventions. A PR that
changes target behaviour carries its change's spec delta (`openspec validate --strict`); a
PR that only touches a v1 mechanism the target drops does not. Until v2 lands the document
above stays the enforced contract.

## Codex adapter

- A repository is installed once before its first delivery. Follow
  [the installation guide](.agent-process/docs/architecture/agent-process-installation.md);
  the installer writes only the documented closed footprint and prints person-owned setup.
- Follow the **Tasks** section of the loaded `agent-process` skill. The
  [delivery overview](.agent-process/docs/architecture/agent-process.md#deterministic-delivery-flow)
  explains the trust boundary without copying the procedure.
- Use `$openspec-propose` for planning and `$openspec-apply-change` for implementation.
  `openspec/config.yaml` points their artifact rules at the shared skill; Codex records
  its architect review as a self-review in `architect-review.md`.
- The advisory control plane (`.agent-process/scripts/agent_orchestrator.py` plus
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
- Follow [Principle V](.agent-process/docs/architecture/principles.md#v-root-cause-before-fix):
  instrument before patching, and observe the live external system when a plan
  depends on how that system is read or classified.
- Never push directly to `main`, force-push, hard-reset, force-delete a branch, or
  self-merge. This publisher temporarily retains repository-specific v1 hooks, but they
  are not distributed; the GitHub ruleset is the portable ref-update barrier.

## Code review

Claude Code Action and Codex automatic review are independent advisory reviewers. The
person enables Codex automatic review during installation; the workflow calls Claude
directly. No process parser or required review verdict turns either result into merge
authority. Before merging, inspect both visible review state and every current-head
`.github/workflows/**` diff because the required quality context is name-bound.
