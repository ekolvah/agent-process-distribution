## MODIFIED Requirements

### Requirement: The plugin's component roots are closed
The plugin component roots at the top level of this repository — the default locations the
plugin reference lists: `.claude-plugin`, `skills/<name>`, a root `SKILL.md`, `commands`,
`agents`, `hooks`, `.mcp.json`, `.lsp.json`, `output-styles`, `workflows`, `themes`, `monitors`,
`bin`, and a root `settings.json` — SHALL be exactly `.claude-plugin`, `agents`, `bin`,
`commands`, `hooks`, and `skills/agent-process`. The installer SHALL render the
`agent-process-marketplace` source of `.claude/settings.json` without `sparsePaths`, and this
repository's own settings SHALL name none.

#### Scenario: Component roots
- **WHEN** the publisher tests read the top level of this repository
- **THEN** the component roots present are exactly `.claude-plugin`, `agents`, `bin`, `commands`, `hooks`, `skills/agent-process`, and any other fails naming it

#### Scenario: Settings render
- **WHEN** the installer renders the settings of any release, or the publisher tests read this repository's settings
- **THEN** the marketplace source has no `sparsePaths`

## ADDED Requirements

### Requirement: The plugin ships the navigation hooks
The plugin SHALL deliver the PreToolUse navigation policy of the implementation requirement
"Shift-left feedback in Claude" as its own hooks for the `Bash` and `Read` tools, running the
policy from the package, so a consumer needs no copy of it. This repository's
`.claude/settings.json` SHALL declare no PreToolUse hook for `Bash` or `Read`.

#### Scenario: Adopted consumer
- **WHEN** the plugin's hook commands run with a project directory that carries `.github/workflows/agent-process.yml` and no copy of the policy, for a `Bash` command with a denied navigation stage and for a whole-file `Read` of a file over the budget
- **THEN** each denies the call and names the tool or range to use instead

#### Scenario: Repository settings carry no navigation hook
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** no PreToolUse entry matches `Bash` or `Read`

### Requirement: Plugin hooks act only in adopted repositories
Every hook command of the plugin SHALL exit 0 with no output when the session's project
directory has no `.github/workflows/agent-process.yml`.

#### Scenario: Unadopted repository
- **WHEN** any hook command of the plugin runs with a project directory that has no `.github/workflows/agent-process.yml`, for an input its policy would deny
- **THEN** it exits 0 with empty stdout
