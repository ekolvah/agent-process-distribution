## ADDED Requirements

### Requirement: A Claude session start takes the agent's token
In a project whose `openspec/config.yaml` holds the agent-process block, the plugin's
session-start hook SHALL append `export GH_TOKEN=<token>` to `CLAUDE_ENV_FILE` when
`git config --get agent-process.bot` in the project names a login, `gh auth token --user <login>`
prints a token, and that token's permission on the repository, read with it, is write or
maintain. Otherwise it SHALL export no `GH_TOKEN`, exit 0, and add to its `systemMessage` and
`additionalContext` `agent-process agent identity not set`, the reason, and the fix: Install
step 6 of the agent-process skill, then the restart of Claude Code. Its output SHALL not carry
the token. In a project without the block it SHALL do neither.

#### Scenario: Token taken
- **WHEN** a session starts in a project with the block, `agent-process.bot` set, and `gh` holding a token for that login with write permission on the repository
- **THEN** the env file exports `GH_TOKEN` as that token, and the hook's output carries neither the token nor `agent-process agent identity not set`

#### Scenario: Identity missing
- **WHEN** a session starts in a project with the block, and `agent-process.bot` is unset, `gh` holds no token for it, or the token's permission is not write or maintain or cannot be read
- **THEN** the env file exports no `GH_TOKEN`, the hook exits 0, and its output names `agent-process agent identity not set`, the reason and the fix

#### Scenario: Project without the block
- **WHEN** a session starts in a project whose `openspec/config.yaml` lacks the block
- **THEN** the env file exports no `GH_TOKEN` and the output does not name `agent-process agent identity not set`

### Requirement: Install's identity step asks nothing
While the dry-run prints the `manual agent-identity` row, Install SHALL show the person the
commands of its agent-identity step with the dry-run's output. After the merge of the
installation PR it SHALL run them without asking, and interrupt the person only for a command
that fails and for the steps only the person can do.

#### Scenario: Identity step after the merge
- **WHEN** the agent reaches the agent-identity step of Install after the installation PR merged
- **THEN** the person saw its commands with the dry-run, the agent runs them without a question to the person, and names to the person a failed command and the person's own steps

## MODIFIED Requirements

### Requirement: Install reports a pending agent identity
`init` SHALL print a `manual agent-identity` row unless the session-start hook's conditions for
taking the agent's token hold in the clone, whatever the session's `GH_TOKEN`. The row SHALL
name the reason the hook's marker would name, and the fix that marker names, and SHALL not
carry the token.

#### Scenario: Identity pending
- **WHEN** a run meets a clone where `agent-process.bot` is unset, `gh` holds no token for it, or the token's permission on the repository is admin or read
- **THEN** its output carries one `manual agent-identity` row naming the missing bot, the missing token or the permission, and the fix

#### Scenario: Identity holds
- **WHEN** a run meets a clone where `agent-process.bot` names a login whose token in `gh` has write permission on the repository
- **THEN** its output carries no `manual agent-identity` row, and the one `gh` call that carried that token as `GH_TOKEN` was a read

## REMOVED Requirements

### Requirement: A Claude session start reports a missing agent identity
**Reason**: The plugin's session-start hook takes the token and reports a missing identity
(`A Claude session start takes the agent's token`); the skill check runs beside it and cannot
see its export.
**Migration**: None for the person; a consumer's skill check loses its identity check at the
next `init` upgrade.
