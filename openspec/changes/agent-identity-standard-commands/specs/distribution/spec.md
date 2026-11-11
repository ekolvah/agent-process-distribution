## MODIFIED Requirements

### Requirement: Install reports a pending agent identity
`init` SHALL print a `manual agent-identity` row unless this clone's
`.claude/settings.local.json` carries an `env.GH_TOKEN` whose permission on the repository,
read with that token in one `gh` call whatever the session's `GH_TOKEN`, is write or maintain.
The row SHALL name the permission read, or that no token is set, and the fix the
session-start identity marker names.

#### Scenario: Identity pending
- **WHEN** a run meets a clone whose settings carry no `env.GH_TOKEN`, or a token whose permission on the repository is admin or read
- **THEN** its output carries one `manual agent-identity` row naming the permission or the missing token, and the fix

#### Scenario: Identity holds
- **WHEN** a run meets a clone whose settings carry a token with write permission on the repository
- **THEN** its output carries no `manual agent-identity` row, and the one `gh` call that carried that token as `GH_TOKEN` was a read

### Requirement: A Claude session start reports a missing agent identity
The installed skill check SHALL stay silent on the identity only when the session's `GH_TOKEN`
equals `env.GH_TOKEN` of the project's `.claude/settings.local.json`. Otherwise, including when
it cannot read that file, it SHALL exit 0 and add a `systemMessage` for the person and an
`additionalContext` for the agent. Each SHALL name `agent-process agent identity not set`, the
reason, and the fix: Install step 6 of the agent-process skill, then the restart of Claude Code.

#### Scenario: Identity missing
- **WHEN** a Claude session starts without `GH_TOKEN`, or with a `GH_TOKEN` that the project's settings do not hold
- **THEN** the check exits 0 and its output names `agent-process agent identity not set` and the fix, to the person and to the agent

#### Scenario: Identity set
- **WHEN** a Claude session starts with the `GH_TOKEN` of the project's settings
- **THEN** the check adds nothing for the identity

### Requirement: Install's admin steps run as the person
`activate_protection` SHALL run each of its `gh` calls without `GH_TOKEN` and `GITHUB_TOKEN`
in its environment.

#### Scenario: A clone with the agent's identity
- **WHEN** `activate_protection` runs with a `GH_TOKEN` in its environment
- **THEN** every `gh` call it issues runs without `GH_TOKEN` and `GITHUB_TOKEN`

### Requirement: Install continues past the installation PR
The Install procedure of the shared skill SHALL, after the confirmed run opens the installation
PR, run `agent-process wait_for_pr <PR>`. On a first exit 3 it SHALL rerun once; a failing
`agent-process / quality` it SHALL fix by a commit on the PR and run it again; review threads and
any other failure, a second exit 3 included, it SHALL show the person, proposing a P0/P1 thread on
an installer-managed file as an issue in `ekolvah/agent-process-distribution`. Once the checks are
green it SHALL ask the person to merge; then, or on exit 4, it SHALL read
`gh pr view <PR> --json state`, on `MERGED` run steps 5 and 6 in the same session — after a
confirm run without asking, only step 5 and only when that run printed the `manual protection`
row — and on any other state show the person the state and stop install.

#### Scenario: Installation PR merged
- **WHEN** the agent follows the skill's Install procedure and the installation PR it opened is merged
- **THEN** `activate_protection` runs and step 6 begins in the same session, without a new request from the person

#### Scenario: Unasked upgrade PR merged
- **WHEN** the PR of a confirm run without asking is merged and that run printed no `manual protection` row
- **THEN** install stops without running `activate_protection` or step 6

## REMOVED Requirements

### Requirement: Agent identity converges
**Reason**: Its transitions are standard commands of Install step 6; the check whose
failure was observed moves into "Install reports a pending agent identity".
**Migration**: None: a repository and clone where `agent_identity --confirm` succeeded keep
their state, and `init` reports the identity as before.
