## MODIFIED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, one
marker-owned Dependabot entry, the skill check `.claude/agent-process-check.py`, and in
`.claude/settings.json` two keys and one `hooks.SessionStart` entry that runs the skill check.
Every other consumer file, key, and hook entry SHALL keep its content, and no publisher file is
copied into the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those five files, and only the two owned settings keys and the owned `SessionStart` entry are added

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release and consumer content beside it, including its own `SessionStart` hooks
- **THEN** only the owned block, files, keys, and hook entry change, and every consumer byte outside them is identical

## ADDED Requirements

### Requirement: A Claude session start reports a missing skill
The installed skill check SHALL pass silently only when `claude plugin list --json` shows exactly
one enabled install of `agent-process@agent-process-marketplace` that applies to the project
(user scope, or a project path equal to the project directory ignoring case) and that install
holds `skills/agent-process/SKILL.md`. In every other case, including a missing or failing CLI,
unparsable output, or an error of the check itself, it SHALL exit 0 with a `systemMessage` for the
person naming `agent-process skill not loaded`, the reason, and the Install URL the hook passes
it (the installed release's `SKILL.md#install`), and an `additionalContext` telling the agent not to reconstruct the skill.

#### Scenario: Skill loaded
- **WHEN** exactly one enabled applicable install holds the skill
- **THEN** the check prints nothing and exits 0

#### Scenario: Skill not loaded
- **WHEN** no enabled install applies, or several distinct installs apply, or the one that applies lacks `skills/agent-process/SKILL.md`
- **THEN** the check exits 0 and its output names `agent-process skill not loaded`, the reason, and the Install URL, to the person and to the agent

#### Scenario: Check cannot decide
- **WHEN** the `claude` CLI is missing, exits non-zero, prints output that is not the expected JSON, or the check raises
- **THEN** the check exits 0 with the same marker naming that reason
