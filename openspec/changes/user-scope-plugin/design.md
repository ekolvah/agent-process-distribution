## Context

See proposal.md — Why for the observations this design rests on. Today Install writes
`enabledPlugins: {agent-process@agent-process-marketplace: true}` into the consumer's
`.claude/settings.json` (`templates/settings.json`, `init._settings_text`), and the machine step
`plugin-channel` only adds the marketplace. The skill check (`templates/skill_check.py::verdict`)
accepts a user or a case-folded project record and treats several distinct ones as not loaded.

## Goals / Non-Goals

**Goals:** no project-scope record is created by our settings; the plugin reaches a machine at
user scope; the check describes what the person must do, without claiming "not loaded" when a
record loads.

**Non-Goals:** predicting which record loads (first-in-file order is observed, not documented);
the installer or the check changing plugin state; the drift message of `start_change`
(`--scope <user|project>` stays true for a legacy record).

## Decisions

- **D1 — user scope only.** The plugin is a personal tool across the person's repositories; the
  docs' user scope matches, it is the one scope Claude Code never keys by cwd, and auto-update
  keeps it current (observed, proposal — Why), so Install's "gets a release within a session"
  holds for it. The project
  keeps `extraKnownMarketplaces` (observed to create no record) so a trusted session still learns
  the marketplace. Alternative: keep `enabledPlugins` and name per-record `update` commands (the
  previous plan) — treats the symptom, and `update` on a spelling miss updates another repository
  (#90519).
- **D2 — Install removes the entry it wrote.** `_settings_text` drops the plugin's `true` entry
  (an `enabledPlugins` left empty stays, as consumer key); a `false` entry stays a conflict (the consumer's choice, as
  today); a settings file not in the form init writes stays a conflict whose hand-edit hint no
  longer names `enabledPlugins`. Already-converged = marketplace entry equal, no plugin entry,
  hooks equal.
- **D3 — the check's rule, in order:** (1) any enabled non-user record whose `projectPath` folds
  to the project → headline `agent-process project-scope install applies`, one `<version>:
  <command>` per such record in listing order; (2) no enabled user record → `agent-process skill
  not loaded` with `not installed at user scope: claude plugin install
  agent-process@agent-process-marketplace`; (3) several distinct enabled user installs → `several
  user-scope installs: <versions>` (today's dedupe by `installPath`, kept as the catcher though the
  CLI keeps one user record); (4) the user install lacks the skill → as today. The
  headline differs in (1) because some record does load; the additionalContext then says to tell
  the person, not "do not reconstruct". `verdict` returns `(headline, reason)` or `None`.
- **D4 — the removal command follows the record's spelling.** `uninstall --scope <scope>` picks
  the record by cwd; only cmd's `cd /d` keeps a lowercase drive letter (observed, #256
  planning), so a `^[A-Za-z]:` path gets `cd /d "<path>" && …` (cmd), any other `cd "<path>" &&
  …`. On a spelling miss `uninstall` exits 1 without touching another record (observed), so a
  wrong shell is visible, not harmful.
- **D5 — test boundary.** The subprocess tests with a fake `claude` stay for the output shape; the
  cmd form is asserted by calling `verdict` loaded with `importlib` from the template (a pure
  function), since a `c:\…` project cannot apply on a Linux runner.

No new script or check: the change edits an existing installer step, template, and check.

## Risks / Trade-offs

- [A collaborator without the `plugin-channel` step] → nothing loads; the check says `not
  installed at user scope` with the install command. Before, a trusted session loaded the
  project-enabled plugin from the known marketplace.
- [Leftover project records on consumer machines] → reported every session with the exact
  removal command until removed; the person runs it once per record.
- [A consumer who wants the plugin off in one repository] → `enabledPlugins: false` in that
  repository's `.claude/settings.local.json` (docs), outside Install.
- [Observations are from `-p` sessions] → the VS Code and CLI records in the person's registry
  (#256) agree with them.

## Migration Plan

Ships in the next release. Per consumer repository: re-run Install and commit the settings
change. Per machine: the `plugin-channel` row's install once, then the removal commands the check
prints. Rollback: revert the PR; old settings re-enable the plugin per project.
