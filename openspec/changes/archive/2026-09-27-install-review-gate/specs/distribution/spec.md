## ADDED Requirements

### Requirement: The consumer review caller runs at the release tag
The installer SHALL render a managed `.github/workflows/agent-review.yml` whose one job
`agent-review` runs on `pull_request` of types `opened` and `synchronize`, calls
`ekolvah/agent-process-distribution/.github/workflows/reusable-agent-review.yml@v<version>`,
and passes only the repository secret `CLAUDE_CODE_OAUTH_TOKEN` as the callee's
`claude_code_oauth_token` and no input, so the check reports as `agent-review / agent-review`.

#### Scenario: Review caller render
- **WHEN** the installer renders the review caller for release `<version>`
- **THEN** its one job `agent-review` calls `reusable-agent-review.yml@v<version>` on `opened` and `synchronize` pull requests, with exactly the secrets the callee declares and no input

### Requirement: The review secret is printed, not set
The plan of a dry-run and of a confirmed run SHALL print, as `manual`, setting the
repository secret `CLAUDE_CODE_OAUTH_TOKEN`, and `init` SHALL issue no command that writes
a secret.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries one `manual` row for the secret, and no command it issued writes a secret

## MODIFIED Requirements

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, one marker-owned Dependabot entry, the skill
check `.claude/agent-process-check.py`, and in `.claude/settings.json` two keys and one
`hooks.SessionStart` entry that runs the skill check. Every other consumer file, key, and
hook entry SHALL keep its content, and no publisher file is copied into the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those six files, and only the two owned settings keys and the owned `SessionStart` entry are added

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release and consumer content beside it, including its own `SessionStart` hooks
- **THEN** only the owned block, files, keys, and hook entry change, and every consumer byte outside them is identical

### Requirement: Protection activation observes quality first
`activate_protection` SHALL exit non-zero before any GitHub write unless two things hold.
The default branch SHALL carry `.github/workflows/agent-process.yml` and
`.github/workflows/agent-review.yml`. The current head of the given PR against the default
branch SHALL have a check run `agent-process / quality` and a check run
`agent-review / agent-review`, each concluded `success` from the GitHub Actions app. The run
SHALL require both contexts, each bound to the integration ID of the app that reported it.

#### Scenario: Caller absent
- **WHEN** the default branch has no `.github/workflows/agent-process.yml` or no `.github/workflows/agent-review.yml`
- **THEN** the run names the missing caller, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Context not observed
- **WHEN** the PR's base is not the default branch, or its current head has no `agent-process / quality` check run, or that run did not succeed, or another app reported it
- **THEN** the run names what it observed on that head, exits non-zero, and every GitHub command it issued is a read

#### Scenario: Review caller present
- **WHEN** the default branch carries both callers and the PR head has successful `agent-process / quality` and `agent-review / agent-review` runs from GitHub Actions
- **THEN** the planned ruleset requires both contexts, each with that app's integration ID

#### Scenario: Review context not observed
- **WHEN** the default branch carries both callers and the PR head has no successful `agent-review / agent-review` run from GitHub Actions
- **THEN** the run names what it observed for that context, exits non-zero, and every GitHub command it issued is a read
