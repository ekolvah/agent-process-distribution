## Context

See `v2-1b-planning-schema/design.md` for the OpenSpec facts; this part only removes. The
delivery scripts of part 1 and the schema of part 2 are on `main` (or in the PRs this one
stacks on) before this PR merges.

## Goals / Non-Goals

**Goals:** one planner, one document that says so. **Non-Goals:** the review gate, the
orchestrator, `open_pr.py` and `roles.yaml` (`v2-4`, `v2-5`); `init` (`v2-2`).

## Decisions

- **Remove, do not deprecate.** Alternative: keep `/plan` as a shim that prints the new
  command — a second entry point to maintain and test for one release.
- **`test_adr_records.py` parses Markdown itself.** Its only import from the removed
  validator was `find_gaps`; a CommonMark parse with `markdown-it` (already a dependency)
  replaces it in twenty lines. Alternative: keep `validate_issue_sections.py` for one
  function — 700 lines for 20.
- **`roles.yaml` keeps its roles, anchors updated.** The advisory control plane is a
  `v2-4` removal; its contract anchors must resolve today (`test_agent_orchestrator`).
- **ADR 0009 is superseded, not deleted.** The catalogue keeps history; the status line is
  the pointer.

## Risks / Trade-offs

- [A consumer repository still calls `/plan`] → the command is gone with a clear "unknown
  command"; the installation guide and `agent-process.md#planning` name the replacement.
- [Doc links to removed anchors] → `test_doc_links` and `test_agent_orchestrator` resolve
  every anchor.

## Migration Plan

One PR on top of part 2; archived through `finish_change`; the person merges. Rollback:
revert the PR — the v1 planner returns beside the OpenSpec route.
