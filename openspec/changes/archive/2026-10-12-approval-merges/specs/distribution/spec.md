## MODIFIED Requirements

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
  reviews dismissed on push;
- the repository's `allow_auto_merge` setting set to true.

A dry-run SHALL issue only reads. A confirmed run SHALL perform the `planned` transitions, then
plan again and exit 1 naming the first transition that is not `unchanged`. A rerun after success
SHALL report every transition `unchanged` and write nothing.

#### Scenario: Confirmed run on a fresh repository
- **WHEN** a confirmed run meets a bot token of `<login>` without admin permission, no invitation, no Project role, settings with other keys and no `GH_TOKEN`, no credential route, no ruleset of that name, and auto-merge not allowed
- **THEN** `<login>` is a collaborator with write access and a Project writer, the clone's settings carry `GH_TOKEN` with every prior key kept, git routes `https://github.com` credentials to `gh`, the ruleset exists with its required approval and no bypass, and the repository allows auto-merge

#### Scenario: A precondition fails
- **WHEN** `.claude/settings.local.json` is not ignored, or `gh` holds no token of `<login>`, or the token's login differs from `--bot`, or `<login>` is a repository admin
- **THEN** the run names the condition, exits 2, and every command it issued is a read

#### Scenario: Rerun
- **WHEN** a confirmed run is repeated after it succeeded
- **THEN** it reports every transition `unchanged` and issues no write
