## Why

After the package foundation ([issue 152](https://github.com/ekolvah/agent-process-distribution/issues/152)) the shared skill exists, but no path installs it: a
consumer repository cannot receive the process and a Codex user cannot link the skill.
The frozen PR [151](https://github.com/ekolvah/agent-process-distribution/pull/151) had an
installer, and its review found the defects one at a time because its tests modelled only
the steady state: the old release rendered a new release's files, the preview of an upgrade
was the old release's plan and then was swallowed, and the confirmed update ran code that had
never been previewed. Two more defects of the same class are observed now, on its head
`096e965`:

- The Codex checkout is created with `git clone --no-checkout` and then
  `git checkout --detach`. Interrupted between the two, the retry classifies the checkout
  as dirty and refuses forever: on 2026-09-23 a `--no-checkout` clone printed
  `D  .agents/skills/.openspec-target` (one line per tracked file) from `git status --porcelain`,
  and `0` lines after the checkout.
- It runs `["npx", ...]` without resolving `npx.cmd`, so the Windows path is never exercised by
  a test that runs it.

Root cause: the lifecycle has transitions — select release, write, interrupt, retry — and
none of them was the unit under test. This change delivers only the local, user-profile, and
consumer-file part of `init` ([parent issue 112](https://github.com/ekolvah/agent-process-distribution/issues/112)),
with a test table over those transitions and without any GitHub write.

## What Changes

- Add `skills/agent-process/scripts/init.py` (stdlib only) with `--test`, optional `--setup`,
  `--version`, and exactly one of `--dry-run` or `--confirm`.
- Add four templates under `skills/agent-process/templates/`: `agent-process.yml` (one
  quality caller), `config.yaml` (marker-owned rules block), `dependabot.yml` (one
  `github-actions` entry), and `settings.json` (two Claude plugin keys pinned to the release).
- Different-version dry-run runs the requested release's own `init.py` from a temporary
  clone and forwards its output and exit code; confirmation first moves the Codex checkout
  to the requested tag and then hands off to that release's `init.py`.
- Every transition reports `planned`, `written`, `unchanged`, or `conflict`; a rerun of the
  same version changes nothing, a retry after interruption does only the unfinished
  transitions, and a consumer-owned, dirty, foreign, or ambiguous input stops the run
  before its first write.
- Add the Claude command `commands/init.md` and an `## Install` section to the shared skill.
- No Project, ruleset, classic protection, required check, secret, commit, or push.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: add the local installer lifecycle — preview, release selection, the Codex
  link, reconcile and retry, fail-closed conflicts, and no remote write; replace the footprint
  requirement of the Copier render with `The installed footprint is closed`, restate the dogfood requirement around
  `init`, as ADR 0027 schedules, instead of the deleted Copier render.

## Impact

- Added: `skills/agent-process/scripts/init.py`,
  `skills/agent-process/templates/agent-process.yml`,
  `skills/agent-process/templates/config.yaml`,
  `skills/agent-process/templates/dependabot.yml`,
  `skills/agent-process/templates/settings.json`, `commands/init.md`, and
  `tests/publisher/test_init.py`.
- Edited: `skills/agent-process/SKILL.md` (`## Install`), `tests/publisher/test_plugin.py`
  and `tests/publisher/test_delivery_scripts.py` (the package now holds `init.py` and the
  four templates), `tests/publisher/test_planning_workflow.py` (its no-`--test` guard covers
  the delivery procedure, not `## Install`), and `.agent-process/docs/architecture/agent-process-installation.md`
  (the retired note points to the Install section).
- Removed: nothing.
- ADR: none. ADR 0027 already decides `init` as the one-command composition; its remote
  steps stay with issues 156 and 154.
- External systems: none. The installer writes the consumer worktree, `~/.agent-process/`,
  and `~/.agents/skills/` only; the release tag it pins is created by the person after the
  sequence of issue 112.
