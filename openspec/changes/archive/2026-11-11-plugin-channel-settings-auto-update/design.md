## Context

The current state, observed at planning time on Claude Code 2.1.296:

- `init` already renders `"autoUpdate": true` on the `agent-process-marketplace` entry of the
  consumer's `.claude/settings.json` (`skills/agent-process/templates/settings.json`).
- `_plugin_channel` (`skills/agent-process/scripts/manual.py`) treats the channel as done only
  when `~/.claude/plugins/known_marketplaces.json` has `autoUpdate: true`, a ref of `stable`,
  and a user-scope install exists. It reads no settings file.
- `claude plugin marketplace add --help` lists only `--claudeai`, `--json`, `--scope` and
  `--sparse`. `claude plugin marketplace update --help` lists only `--json`.

Documentation, quoted:

- loading.md, "Which marketplaces and plugins auto-update": "Whether a marketplace
  auto-updates follows the first of these that is set: 1. `autoUpdate` on its
  `extraKnownMarketplaces` entry in a settings file 2. `autoUpdate` on its
  `known_marketplaces.json` entry, which the Enable auto-update toggle under `/plugin`
  Marketplaces writes. When a settings file also declares the marketplace under
  `extraKnownMarketplaces`, the toggle writes `autoUpdate` to that settings entry as well".
- loading.md: "When you run `claude plugin marketplace add`, Claude Code writes the marketplace
  to `extraKnownMarketplaces` in your user settings as well as to disk".
- host-marketplace.md, "Turn on auto-update": "A user or an admin turns it on", via the UI
  toggle or `"autoUpdate": true` on the `extraKnownMarketplaces` entry in managed settings.
- org.md: the `extraKnownMarketplaces` entries of a repository's `.claude/settings.json`
  "apply only in a folder the contributor has trusted".

## Goals / Non-Goals

**Goals:** the `plugin-channel` row has no UI step, and the check sees the user-settings write.

**Non-Goals:**

- Installing the plugin by declaration alone. Under `-p` it was observed not to complete:
  `installed_plugins.json` stayed empty.
- Reading managed or project settings in the check (decision 3).

## Decisions

### 1. The user-settings entry turns auto-update on, no flag does

No CLI flag or environment variable turns auto-update on. `FORCE_AUTOUPDATE_PLUGINS=1` only
keeps the pass running when the `DISABLE_*` variables turn it off (loading.md, same section).
These runs took place at planning time in an isolated `CLAUDE_CONFIG_DIR` on Claude Code
2.1.296. Each run was `claude -p "say ok" --debug` from a scratch folder.

- `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"` printed
  "Successfully added marketplace: agent-process-marketplace (declared in user settings)". It
  wrote the user-settings entry without `autoUpdate`, and it rewrote an entry that already
  carried `"autoUpdate": true` without the key.
- With `"autoUpdate": true` on the user-settings entry, the run logs "Synced autoUpdate=true
  from settings for marketplace: agent-process-marketplace", and `known_marketplaces.json` then
  reads `"autoUpdate": true`. Without the key, the log names no marketplace and the file is
  unchanged.
- The same entry in a trusted folder's `.claude/settings.json` produced no sync line. With
  only that file declaring the marketplace, the run logged "installPluginsForHeadless: no
  marketplaces declared". An interactive session was not observed. The earlier interactive
  project-only run had no positive control
  (`archive/2026-09-28-releases-through-auto-update`, proposal Why).

### 2. The row names the settings write after `add` and `install`

The row becomes: `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`,
then `claude plugin install agent-process@agent-process-marketplace`, then set
`"autoUpdate": true` on the `agent-process-marketplace` entry of `~/.claude/settings.json`.
The write goes last because `add` drops the key (decision 1). README's install block and
SKILL.md's migration text name the same three steps.

Alternatives:

- A new `agent-process` subcommand that writes the key. The row is for a machine without the
  plugin, and README runs these steps in a terminal outside Claude Code. There
  `agent-process` is not on `PATH`, because the plugin's `bin/` is added only for Claude's own
  shell.
- A `python -c` one-liner. Its quoting differs between PowerShell and POSIX shells, the two
  shells the process supports.
- `init` writes the key. That breaks the requirement that `init` issues no command changing
  plugin or marketplace state, and the write would land outside the repository.
- Rely on the project entry `init` renders. It is unobserved to sync (decision 1), and it
  would apply only in trusted repositories. If an interactive session does sync it, the sync
  lands in `known_marketplaces.json`. The check falls back to that file, so the row closes
  without the write.

### 3. `_plugin_channel` reads the user-settings `autoUpdate` first

Once the source, `stable` ref and user-scope install hold, `_plugin_channel` reads
`~/.claude/settings.json` through `_plugin_file`. If the `agent-process-marketplace` entry
under `extraKnownMarketplaces` has an `autoUpdate` key, the check requires it to be `true`.
Otherwise it requires the known-marketplace entry's `autoUpdate` to be `true`, as it does
today. This is loading.md's precedence restricted to user settings (proposal Why). Managed
settings are an admin's route (host-marketplace.md), and the row addresses a person.

Input failure modes:

- A missing settings file, or one without the entry or the key, leads to the known-marketplace
  entry, for example after a later `add` drops the key. That is today's behaviour.
- Malformed JSON or an unexpected shape raises `Unreadable`, and the row prints
  `(cannot read: …)`. That is the existing path for the plugin files.

## Risks / Trade-offs

- [A later Claude Code release changes the precedence or the sync, so a machine that did the
  row stops auto-updating] → at session start in an adopted repository whose
  `openspec/config.yaml` records a newer release, the plugin prints `agent-process release
  drift` with the `claude plugin update` fix (`plugin_env.py` → `init.release_drift`).

## Migration / Rollback

There is no data migration. A machine set through the UI stays done (proposal Impact).
Rollback is a revert of the PR.
