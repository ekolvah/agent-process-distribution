## MODIFIED Requirements

### Requirement: This repository dogfoods its own process
This repository SHALL expose the shared Claude plugin/skill package that its installer installs
in consumers, and its `.claude/settings.json` SHALL declare the marketplace and enable no plugin,
as a consumer's does. Repository sessions and publisher tests SHALL exercise the
shared skill source, its portable scripts, its installer and templates, its OpenSpec rule
pointers, and its package-version identity. Repository-only settings and v1 process files
SHALL NOT be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, the installer or a template, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its delivery gates remain intact

#### Scenario: Repository settings
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** it declares `agent-process-marketplace`, runs the skill check at session start, and has no `enabledPlugins` entry for `agent-process@agent-process-marketplace`

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, one marker-owned Dependabot entry, the skill
check `.claude/agent-process-check.py`, and in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`. Every other consumer file, key, and hook entry SHALL keep its content, and
no publisher file is copied into the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those six files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical

### Requirement: A Claude session start reports a missing skill
The installed skill check SHALL read `claude plugin list --json`. When an enabled install of
`agent-process@agent-process-marketplace` of a scope other than user has a project path equal to
the project directory ignoring case, it SHALL exit 0 with a `systemMessage` for the person naming
`agent-process project-scope install applies`, the Install URL the hook passes it, and, for each
such install, its version and the command that removes it: `cd /d "<projectPath>"` (a path with a
drive letter) or `cd "<projectPath>"` (any other path) with the install's exact `projectPath`
spelling, followed by `&& claude plugin uninstall agent-process@agent-process-marketplace --scope
<its scope>`; and an `additionalContext` telling the agent to tell the person. Otherwise it SHALL
pass silently only when exactly one enabled user-scope install exists and it holds
`skills/agent-process/SKILL.md`. In every other case, including a missing or failing CLI,
unparsable output, or an error of the check itself, it SHALL exit 0 with a `systemMessage` for the
person naming `agent-process skill not loaded`, the reason, and the Install URL (the Install
section of the installed release's skill), and an `additionalContext` telling the agent not to
reconstruct the skill; when no enabled user-scope install exists, the reason SHALL name `claude
plugin install agent-process@agent-process-marketplace`.

#### Scenario: Skill loaded
- **WHEN** exactly one enabled user-scope install holds the skill and no other-scope install applies to the project
- **THEN** the check prints nothing and exits 0

#### Scenario: Project-scope install applies
- **WHEN** a user-scope install and two project-scope installs of the project whose `projectPath` differs only in drive-letter case are listed
- **THEN** the output names `agent-process project-scope install applies`, not `agent-process skill not loaded`, the Install URL, and for each project-scope install `cd /d "<its projectPath>" && claude plugin uninstall agent-process@agent-process-marketplace --scope project` with that install's spelling

#### Scenario: Skill not loaded
- **WHEN** no enabled user-scope install exists, several distinct ones exist, or the one that exists lacks `skills/agent-process/SKILL.md`
- **THEN** the check exits 0 and its output names `agent-process skill not loaded`, the reason, and the Install URL, to the person and to the agent, and a missing user-scope install's reason names `claude plugin install agent-process@agent-process-marketplace`

#### Scenario: Check cannot decide
- **WHEN** the `claude` CLI is missing, exits non-zero, prints output that is not the expected JSON, or the check raises
- **THEN** the check exits 0 with the `agent-process skill not loaded` marker naming that reason

### Requirement: The marketplace follows the stable channel
The installer SHALL render the `agent-process-marketplace` declaration of
`.claude/settings.json` with the source `ref` `stable` and `"autoUpdate": true`, for every
release. The plan of a dry-run and of a confirmed run SHALL print, as `manual`, the once-per-machine
step that declares the marketplace at `stable` in user settings, enables its auto-update, and
installs the plugin at user scope, and `init` SHALL issue no command that changes plugin or
marketplace state.

#### Scenario: Channel render
- **WHEN** the installer renders the settings of any release
- **THEN** the marketplace source's `ref` is `stable` and the marketplace entry's `autoUpdate` is `true`

#### Scenario: Machine channel step
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries one `manual plugin-channel` row naming `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`, enabling auto-update, and `claude plugin install agent-process@agent-process-marketplace`, and no command it issued is a `claude` command
