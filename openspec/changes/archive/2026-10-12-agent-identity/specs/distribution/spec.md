## ADDED Requirements

### Requirement: Agent identity converges
`agent-process agent_identity --bot <login>` SHALL run from a consumer root with `--dry-run`
or `--confirm`. It SHALL refuse with exit 2 before any write when any of these holds:
- `.claude/settings.local.json` is not git-ignored in this clone;
- `gh auth token --user <login>` yields no token;
- that token's `gh api user` login is not `<login>`;
- `<login>` holds the admin permission on the repository.

It SHALL print one line per transition, marked `planned` or `unchanged`. The transitions are:
- the repository collaborator invitation of `<login>` and its acceptance with `<login>`'s token;
- `<login>`'s write role on the Project linked to the repository;
- `env.GH_TOKEN` of this clone's `.claude/settings.local.json` set to that token, every other
  key of the file kept;
- this clone's git config: the `https://github.com` credential helper list reset and routed to
  `gh auth git-credential`;
- one repository ruleset named `agent-process person approves` on the default branch, with no
  bypass actor, whose only rule is `pull_request` with one required approving review and stale
  reviews dismissed on push.

A dry-run SHALL issue only reads. A confirmed run SHALL perform the `planned` transitions, then
plan again and exit 1 naming the first transition that is not `unchanged`. A rerun after success
SHALL report every transition `unchanged` and write nothing.

#### Scenario: Confirmed run on a fresh repository
- **WHEN** a confirmed run meets a bot token of `<login>` without admin permission, no invitation, no Project role, settings with other keys and no `GH_TOKEN`, no credential route, and no ruleset of that name
- **THEN** `<login>` is a collaborator with write access and a Project writer, the clone's settings carry `GH_TOKEN` with every prior key kept, git routes `https://github.com` credentials to `gh`, and the ruleset exists with its required approval and no bypass

#### Scenario: A precondition fails
- **WHEN** `.claude/settings.local.json` is not ignored, or `gh` holds no token of `<login>`, or the token's login differs from `--bot`, or `<login>` is a repository admin
- **THEN** the run names the condition, exits 2, and every command it issued is a read

#### Scenario: Rerun
- **WHEN** a confirmed run is repeated after it succeeded
- **THEN** it reports every transition `unchanged` and issues no write

### Requirement: A Claude session start reports a missing agent identity
The installed skill check SHALL stay silent on the identity only when the session's `GH_TOKEN`
equals `env.GH_TOKEN` of the project's `.claude/settings.local.json`. Otherwise, including when
it cannot read that file, it SHALL exit 0 and add a `systemMessage` for the person and an
`additionalContext` for the agent. Each SHALL name `agent-process agent identity not set`, the
reason, and the `agent-process agent_identity --bot <login> --dry-run` command.

#### Scenario: Identity missing
- **WHEN** a Claude session starts without `GH_TOKEN`, or with a `GH_TOKEN` that the project's settings do not hold
- **THEN** the check exits 0 and its output names `agent-process agent identity not set` and the command, to the person and to the agent

#### Scenario: Identity set
- **WHEN** a Claude session starts with the `GH_TOKEN` of the project's settings
- **THEN** the check adds nothing for the identity

## MODIFIED Requirements

### Requirement: Releases go through release-please
A release SHALL be cut by `release-please` alone: on a push to `main` it SHALL open or
update one release PR whose version follows the Conventional Commit types on `main` since the
last release, and that PR SHALL move every version place — `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `VERSION` in `skills/agent-process/scripts/init.py` and
the release manifest — to that version in one commit. The release PR SHALL be opened with a
token whose events start workflows, so the required contexts run on it. The release workflow
SHALL approve the PR it opened or updated with the workflow's own `GITHUB_TOKEN`, and then
enable auto-merge with squash on it with the release token. The repository SHALL allow
auto-merge and allow GitHub Actions to approve pull requests; a failure of either step SHALL
fail the workflow run. A run that opens or updates no release PR SHALL succeed without
approving or enabling auto-merge.
Merging the release PR SHALL create the tag `v<version>` and its GitHub Release; no person or
script sets a release tag by hand.

#### Scenario: Version places agree
- **WHEN** the tests run on any head, including a release PR's
- **THEN** every version place equals the version of the release manifest, and the release-please configuration names each place

#### Scenario: Release PR opened or updated
- **WHEN** the release workflow opens or updates the release PR
- **THEN** `github-actions` approves that PR and auto-merge with squash is enabled on it, or the workflow run fails

#### Scenario: No release PR change
- **WHEN** the release workflow runs and opens or updates no release PR
- **THEN** the workflow run succeeds and the approval and auto-merge steps are skipped

#### Scenario: Release PR merged
- **WHEN** the release PR of version `<version>` merges once its required checks pass
- **THEN** the tag `v<version>` and a GitHub Release of that tag exist on the merge commit

## REMOVED Requirements

### Requirement: The plugin ships the git guard
**Reason**: Once `agent_identity` has run, the agent acts as a non-admin collaborator, and
GitHub refuses its merge until the person approves, however the command is written ("The
person approves"). The
default-branch ruleset refuses a push to `main` and a force push to it. The guard had no organic
denial since it shipped.

**Migration**: Run `agent-process agent_identity --bot <login>` in each adopted repository and
clone. Until then, each session start prints `agent-process agent identity not set`.
