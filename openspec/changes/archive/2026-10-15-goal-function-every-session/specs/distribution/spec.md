## ADDED Requirements

### Requirement: An installed repository's sessions carry the goal function
A confirmed installer run SHALL write the managed `.claude/rules/agent-process.md`: the line
`# agent-process:managed`, a blank line, then the installing release's
`skills/agent-process/always-on.md`, which holds the `## Goal function` and `## Claude harness`
sections and no `paths` frontmatter. An existing file without that first line SHALL be a
`conflict`.

#### Scenario: Rules file written
- **WHEN** a confirmed run installs into a fresh repository, and again into one that carries another release's rules file
- **THEN** `.claude/rules/agent-process.md` is the marker line, a blank line and the release's `always-on.md`, and that text starts with no `---` frontmatter and holds `## Goal function` and `## Claude harness`

#### Scenario: Unmanaged rules file
- **WHEN** a dry-run meets a `.claude/rules/agent-process.md` whose first line is not `# agent-process:managed`
- **THEN** it prints `conflict` for `rules`, exits non-zero, and no consumer file has changed

## MODIFIED Requirements

### Requirement: This repository dogfoods its own process
This repository SHALL expose the shared Claude plugin/skill package that its installer installs
in consumers, and its `.claude/settings.json` SHALL declare the marketplace and enable no plugin,
as a consumer's does. Its `CLAUDE.md` SHALL import `@skills/agent-process/always-on.md`, the
source of the rules file a consumer gets. Repository sessions and publisher tests SHALL exercise
the shared skill source, its portable scripts, its installer and templates, its OpenSpec rule
pointers, and its package-version identity. Repository-only settings and v1 process files
SHALL NOT be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, the installer or a template, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its delivery gates remain intact

#### Scenario: Repository settings
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** it declares `agent-process-marketplace`, runs the skill check at session start, and has no `enabledPlugins` entry for `agent-process@agent-process-marketplace`

#### Scenario: Repository instructions
- **WHEN** the publisher tests read this repository's `CLAUDE.md`
- **THEN** one of its lines is `@skills/agent-process/always-on.md`

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, the managed
`.github/workflows/task-readings.yml`, one marker-owned Dependabot entry, the
marker-owned block of `.pre-commit-config.yaml` — the whole file when the run creates it —, the
seeded `.github/agent-process-quality.json`, the skill
check `.claude/agent-process-check.py`, the managed rules file `.claude/rules/agent-process.md`,
in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`, and, outside the working tree, the
pre-push hook of this clone that `pre-commit install --hook-type pre-push` writes. Every other
consumer file, key, and hook entry SHALL keep its content, and no publisher file is copied into
the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those ten files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical
