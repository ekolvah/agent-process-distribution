## Why

A consumer machine never moves to a new release by itself (#199): Install writes the
marketplace declaration with `ref: v<version>`, auto-update is off for a third-party
marketplace by default, and a project's `ref` does not re-point a marketplace the machine
already knows (#184). Auto-update re-reads the declared ref, so a tag pin never sees a newer
release. An earlier change kept the release on `main` tags (`sparsePaths`, no release
branch) (#216), so the channel ref is this change's decision.

Platform behaviour, observed with Claude Code 2.1.283 on Windows (the table of steps 1–5 is on
record in the [#199 comment](https://github.com/ekolvah/agent-process-distribution/issues/199#issuecomment-5859573019)):

- `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"` re-points a known
  marketplace once the user declaration names the same ref (step 3).
- Positive control of step 5, 2026-09-28: user declaration `ref: stable`, `"autoUpdate": true`;
  `known_marketplaces.json` carries `"autoUpdate": true`, the clone at `v2.6.0`, every install
  at `2.0.0`. An interactive session started 04:52:56Z; at 04:57:29Z `known_marketplaces.json`
  `lastUpdated` moved and `installed_plugins.json` recorded `2.6.0` for the user install and for
  the project install of that session's path (`c:\…\agent-process-distribution`), while the
  install of `C:\…\agent-process-distribution` and of `agent-process-sandbox` stayed `2.0.0`.
  This matches the reference (code.claude.com/docs/en/plugins/loading, "When auto-update runs":
  "after you send your first message, Claude Code waits a random delay of up to ten minutes. It
  then refreshes every marketplace with auto-update on and updates the plugins installed from
  them on disk").
- The same page: whether a marketplace auto-updates follows first "`autoUpdate` on its
  `extraKnownMarketplaces` entry in a settings file". A project-only `autoUpdate` (step 4) showed
  no update, but without a positive control then; it is not relied on.
- 2026-09-28 05:24Z, from `C:\…\agent-process-distribution` (its install still `2.0.0`):
  `claude plugin update agent-process@agent-process-marketplace --scope project --json` printed
  `"updateOutcome":"updated","oldVersion":"2.0.0","newVersion":"2.6.0"`, and
  `known_marketplaces.json` `lastUpdated` moved to 05:24:11.740Z just before the install record
  (05:24:11.832Z): the update refreshes the marketplace itself.
- A Dependabot PR that bumps only `quality.yml@v<x.y.z>` leaves the rest of the install on the
  old release and fails only on `PR links no issue` (#199 comment, "Decided").

## What Changes

- **BREAKING** (per machine, once): the marketplace follows the `stable` branch. Install renders
  the declaration with `ref: stable` and `"autoUpdate": true`; the release workflow
  fast-forwards `stable` to the commit it tagged. A machine still on a tag gets no newer
  release until it migrates; the migration steps ship as the `BREAKING CHANGE` note of release
  3.0.0. Install prints the same once-per-machine step as a `manual plugin-channel` row, so a
  fresh machine does not rest on the project `autoUpdate` alone.
- The release-drift fix for a skill older than the project names
  `claude plugin update agent-process@agent-process-marketplace --scope <scope>` and a restart,
  never a pin to
  `#v<x.y.z>`, which would stop auto-update (PR #198).
- Install's managed Dependabot entry ignores `ekolvah/agent-process-distribution`: a release
  reaches the repository through release drift and re-running Install, not a half-update PR.
- Non-goal: the duplicate install records by drive-letter case (design, Risks).

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the marketplace follows the `stable` channel with auto-update, and Install
  prints the machine step (ADDED); a
  release moves `stable` (ADDED); the managed Dependabot entry leaves process refs to Install
  (ADDED); the release-drift fix names a plugin update (MODIFIED).

## Impact

- Edited: `skills/agent-process/templates/settings.json` (`ref`, `autoUpdate`),
  `skills/agent-process/templates/dependabot.yml` (`ignore`),
  `skills/agent-process/scripts/init.py` (`release_drift` fix text, `_manual` row, docstring),
  `.github/workflows/release-please.yml` (move `stable`),
  `skills/agent-process/SKILL.md` (Install: channel, fix, migration),
  `tests/publisher/test_plugin.py`, `tests/publisher/test_init_remote.py`,
  `tests/publisher/test_init_config.py`, `tests/publisher/test_start_change.py`,
  `tests/publisher/test_reusable_workflows.py`, `tests/publisher/test_planning_workflow.py`,
  `openspec/specs/distribution/spec.md` (by archive).
- Added: none. Removed: none. No ADR: the channel decision is recorded in this change's
  `design.md`, archived with it; ADRs 0030/0031 (release-please, auto-merge) stay valid.
- This repository's `.claude/settings.json` keeps tracking the default branch (dogfood).
- Release 3.0.0 (the override in the PR body) and a `quality.yml@v3.0.0` consumer caller.
