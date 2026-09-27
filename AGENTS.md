# Repository agent guidance

The process is specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec) and is the
source of truth: `openspec/specs/` holds what is implemented, `openspec/changes/` what is
pending (the tracking issue #107 lists the v2 changes), `openspec/config.yaml` the repository
context, and [`skills/agent-process/SKILL.md`](skills/agent-process/SKILL.md) the portable
procedure. A PR that changes behaviour carries its change's spec delta
(`openspec validate --strict`).

## Repository conventions

- Capture Python subprocess output with `encoding="utf-8"`; do not turn a
  `None` stdout or stderr into an empty string.
- Keep a PR to one logical unit. Update planned docs and ADRs, or explicitly
  record why they do not apply.
- Follow [Principle V](skills/agent-process/principles.md#v-root-cause-before-fix):
  instrument before patching, and observe the live external system when a plan
  depends on how that system is read or classified.
- Never bypass hooks, push directly to `main`, force-push, hard-reset,
  force-delete a branch, or self-merge. The repository hook is supplementary;
  GitHub branch protection remains the final barrier.

## Code review

The Claude review job of the `agent-review` workflow reviews every PR head; its reporting
contract is [REVIEW_CONTRACT.md](.agent-process/REVIEW_CONTRACT.md). The gate's parser and
enforcement code come from the default branch, but the review is evidence, not a substitute
for the platform workflow-definition trust anchor.
