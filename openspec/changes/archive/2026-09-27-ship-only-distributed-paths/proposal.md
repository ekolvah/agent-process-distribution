## Why

A consumer receives the whole repository (#216) through two carriers:

- the plugin: `.claude/settings.json` registers `agent-process-marketplace` as a `github`
  source and the plugin entry's `source` is `"."`, so the marketplace clone and the plugin cache
  hold the repository root. Observed in this machine's cache
  `~/.claude/plugins/cache/agent-process-marketplace/agent-process/2.0.0/`: `.claude/skills`,
  `.agents/skills` and the rest of the development tree beside `skills/agent-process`;
  `git archive HEAD` is 2.8 MB, of which `openspec/` is 1.8 MB, `tests/` 0.4 MB,
  `.agent-process/docs` 0.2 MB, while the package (`skills/agent-process`, `agents`,
  `commands`, `.claude-plugin`) is under 0.2 MB;
- the installer: `init.py` keeps a full clone at `~/.agent-process/distribution`. Since
  remove-codex its only reader is the `--confirm` hand-off to another release
  (remove-codex design D5 deferred removing it as a separate decision).

Platform behaviour, observed 2026-09-27 with Claude Code 2.1.283 in an isolated
`CLAUDE_CONFIG_DIR`: `claude plugin marketplace add
"https://github.com/ekolvah/agent-process-distribution.git#v2.6.0" --sparse .claude-plugin
skills/agent-process agents commands` recorded
`'sparsePaths': ['.claude-plugin', 'skills/agent-process', 'agents', 'commands']` in
`known_marketplaces.json`; `claude plugin install agent-process@agent-process-marketplace`
succeeded and the cache `agent-process/2.6.0/` held 225K: `.claude-plugin`, `agents`,
`commands`, `skills`, plus the root files `AGENTS.md`, `CHANGELOG.md`, `pyproject.toml`,
`release-please-config.json`, `.gitignore`, `.release-please-manifest.json` (cone mode keeps
root files). The reference lists `sparsePaths` as a field of the `github` marketplace source
in `extraKnownMarketplaces` (code.claude.com/docs/en/plugins/marketplace-reference, "Fields by
type": "Array of directories for a sparse checkout").

## What Changes

- The installer renders the marketplace source with `sparsePaths` naming the package
  directories; this repository's own settings name the same list.
- The user-scope checkout is removed: `init --confirm` of another release hands off from a
  temporary clone removed afterwards, as `--dry-run` already does. The `checkout` transition,
  its conflicts (dirty, other origin, not a repository, parent not a directory) and the
  persistent `~/.agent-process/distribution` go away. Nothing reads it any more; an existing
  one is left in place, unused.
- Non-goal: the CI trusted checkouts of `quality.yml` and `reusable-agent-review.yml` keep
  checking out the callee at `job.workflow_sha`; they are ephemeral runner state, not
  something a consumer keeps.

## Capabilities

### New Capabilities

### Modified Capabilities
- `distribution`: the plugin marketplace fetches only the package (ADDED); confirmation
  selects the release from a temporary checkout and keeps no process checkout in the user
  profile; the checkout conflicts leave the fail-closed requirement.

## Impact

- Edited: `skills/agent-process/templates/settings.json` (`sparsePaths`),
  `.claude/settings.json` (same list), `skills/agent-process/scripts/init.py` (checkout step,
  `Context.checkout`, `_same_path` and the docstring removed; confirm hand-off from a
  temporary clone), `tests/publisher/init_harness.py` (`Sandbox.checkout`, `LABELS`),
  `tests/publisher/test_init.py`, `tests/publisher/test_init_conflicts.py`,
  `tests/publisher/test_plugin.py`, `openspec/specs/distribution/spec.md` (by archive).
- Added: none. Removed: none.
- Consumer machines: a marketplace the machine already knows is not re-cloned by a changed
  settings entry (#184); it turns sparse on its next fresh add. An old release run through
  the hand-off (`--version 2.6.0`) still writes its own checkout — that release owns its run.
