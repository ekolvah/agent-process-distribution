## Why

The cleanup audit of 2026-09-27 found tracked leftovers that no change owns:

- `.claude-plugin/plugin.json:7` (`author.name`) and `.claude-plugin/marketplace.json:5`
  (`owner.name`) read `kinozal_scraper maintainers`, the origin project; this repository and
  its plugin belong to `ekolvah`.
- `.agent-process/scripts/navigation_policy.py:281-283` names "the existing
  `.agent-process/scripts/token_trend.py`" as the measurer of its revision condition. The file
  never existed here: `git log --all --oneline -- '*token_trend*'` prints nothing.
- `AGENTS.md:29-31` keeps the template placeholder `<!-- List this project's own recurring
  environment pitfalls here … -->` as an empty first bullet of "Repository conventions".
- `docs/telemetry-measurement-setup.md` is the only file of `docs/`; every other document of the
  process lives under `.agent-process/docs/`.

## What Changes

- Both manifests name `ekolvah`.
- The revision condition of `navigation_policy.py` drops the non-existent measurer and keeps
  its rule (tighten or revert when refusals do not reduce the growth).
- The placeholder bullet leaves `AGENTS.md`.
- `git mv docs/telemetry-measurement-setup.md .agent-process/docs/`; its two ADR links and the
  link of ADR 0026 to it follow; `docs/` disappears.

## Capabilities

### New Capabilities

### Modified Capabilities

None. No requirement names these files or their content, so the change sets `skip_specs: true`.

## Impact

- Moved: `docs/telemetry-measurement-setup.md` → `.agent-process/docs/telemetry-measurement-setup.md`.
- Edited: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `.agent-process/scripts/navigation_policy.py` (docstring only), `AGENTS.md`,
  `.agent-process/docs/adr/0026-project-attribution-rides-the-telemetry-resource-attributes.md`
  (one link).
- Not touched: the `kinozal` strings in `tests/publisher/test_hooks.py` and
  `tests/agent_process/test_doc_links.py` (test inputs, not leftovers); the review-gate split
  (#215) and the shipped tree (#216), tracked separately.
