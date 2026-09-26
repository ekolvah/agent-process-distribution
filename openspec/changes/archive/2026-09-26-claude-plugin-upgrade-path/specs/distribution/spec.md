## MODIFIED Requirements

### Requirement: Delivery entry scripts refuse release drift
The installer SHALL record the installed release as the line `# agent-process release: <version>`
in its `openspec/config.yaml` block. `create_tracking_issue` and `start_change` SHALL read that
line before any other step and, when it is absent, not a `<major>.<minor>.<patch>` version, or
different from the release of the running skill, exit 2 without a GitHub call, naming both
releases and the fix: re-run Install with the running skill when the project's release is absent,
unparsable or older. When the skill's release is older, the fix SHALL name, for Claude, the
user-scope marketplace declaration at `v<recorded>` (`claude plugin marketplace add`, run outside any project,
with "ekolvah/agent-process-distribution#v<recorded>"`, or an edit of the declaration in
`~/.claude/settings.json`), a restart, `claude plugin update
agent-process@agent-process-marketplace` for each install scope and a restart. For Codex it
SHALL name Install with `--version <recorded>` and a restart. It SHALL NOT name
`/plugin marketplace update`. Scripts run from `skills/agent-process/scripts` under the repository
root SHALL skip the comparison.

#### Scenario: Release recorded
- **WHEN** a confirmed installer run writes the `openspec/config.yaml` block
- **THEN** the block holds `# agent-process release: <version>` of the installed release

#### Scenario: Release drift
- **WHEN** `create_tracking_issue` or `start_change` runs from a skill outside the repository's `skills/agent-process/scripts` and the recorded release is absent, unparsable, older or newer than the skill's
- **THEN** it exits 2 before any GitHub call, and its message names both releases and the fix for that direction

#### Scenario: Skill behind the project
- **WHEN** either script runs from a skill whose release is older than the recorded one
- **THEN** its message names `claude plugin marketplace add "ekolvah/agent-process-distribution#v<recorded>"`, `~/.claude/settings.json`, `claude plugin update agent-process@agent-process-marketplace` and `--version <recorded>`, and does not name `/plugin marketplace update`

#### Scenario: Publisher checkout
- **WHEN** either script runs from `<root>/skills/agent-process/scripts` of a repository whose config records no release
- **THEN** it proceeds past the comparison
