## MODIFIED Requirements

### Requirement: The marketplace follows the stable channel
The installer SHALL render the `agent-process-marketplace` declaration of
`.claude/settings.json` with the source `ref` `stable` and `"autoUpdate": true`, for every
release. A run SHALL print, as `manual`, the once-per-machine step that declares the
marketplace at `stable` in user settings, installs the plugin at user scope, and then sets
`"autoUpdate": true` on the marketplace's entry in user settings, while the machine's known
marketplace is not at `stable`, its auto-update is off, or the plugin has no user-scope
install. Auto-update SHALL be read from the `autoUpdate` of the marketplace's user-settings
entry when that entry sets one, else from that of its known-marketplace entry. `init` SHALL issue no command that changes plugin or marketplace state.

#### Scenario: Channel render
- **WHEN** the installer renders the settings of any release
- **THEN** the marketplace source's `ref` is `stable` and the marketplace entry's `autoUpdate` is `true`

#### Scenario: Machine channel step
- **WHEN** a dry-run or confirmed run completes on a machine without the marketplace
- **THEN** its output carries one `manual plugin-channel` row naming, in this order, `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`, `claude plugin install agent-process@agent-process-marketplace` and `"autoUpdate": true` in `~/.claude/settings.json`, the row names no `/plugin` step, and no command the run issued is a `claude` command

#### Scenario: Auto-update read from user settings
- **WHEN** a run completes with the known marketplace at `stable` and the plugin installed at user scope, and the user-settings entry of the marketplace sets `autoUpdate` to the opposite of its known-marketplace entry
- **THEN** its output carries a `manual plugin-channel` row exactly when the user-settings `autoUpdate` is not `true`
