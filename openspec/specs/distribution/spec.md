# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

### Requirement: CI runs the trusted driver, not the PR's copy
An installed consumer's quality job SHALL invoke the reusable workflow from this
repository at the immutable tag its caller pins. The publisher's own quality job SHALL
instead invoke its repository-local reusable workflow so the change that introduces or
updates that workflow can create a runnable check before its release tag exists. The
reusable workflow SHALL read the PR-to-issue link, run the caller's declared `setup` and
`test` commands against the PR worktree, and validate OpenSpec there. A consumer PR SHALL
NOT replace the reusable workflow implementation selected by the pinned ref. The
publisher's local workflow changes SHALL be inspected on the settled current head before
the person merges.

#### Scenario: Quality check on a PR
- **WHEN** the quality workflow runs for a consumer PR
- **THEN** its process-owned steps come from the immutable tagged reusable workflow and its caller-declared commands run against the PR head

#### Scenario: Quality check on the publisher PR
- **WHEN** this publisher changes the reusable quality workflow before the matching release tag exists
- **THEN** its caller uses the repository-local reusable workflow from the same PR head and GitHub creates the `quality / quality` job

### Requirement: The process footprint is one root plus a closed exception set
A consumer SHALL receive only the files OpenSpec generates for Claude and Codex,
`openspec/config.yaml`, the two process-owned keys in `.claude/settings.json`, one
`.github/workflows/agent-process.yml`, and the process entry in
`.github/dependabot.yml`. The Codex skill SHALL be a user-level link outside the
repository. The process SHALL NOT install `.agent-process/`, hooks, an `AGENTS.md`
fragment, a report-path convention, or publisher tests into the consumer.

#### Scenario: Rendered payload
- **WHEN** `init` completes in a consumer repository
- **THEN** every repository file it added is in the closed set and none is a copy of a process script

### Requirement: This repository dogfoods its own process
This repository SHALL enable its local marketplace plugin, use the same one-caller shape
and reusable quality workflow that `init` installs, and carry the same pointer-rule shape
in `openspec/config.yaml`. Repository-specific settings MAY remain in addition to the two
portable plugin keys and SHALL NOT be emitted into consumers.

#### Scenario: Process change
- **WHEN** the skill, caller template, init behavior, or reusable quality workflow changes
- **THEN** publisher tests and this repository's own sessions or CI exercise the changed source before a consumer release

### Requirement: One command installs the process
One command, `init`, run from either carrier in a consumer repository, SHALL install or
update the process. It SHALL run OpenSpec for Claude and Codex, write the process
configuration and one workflow caller, merge the two plugin-enablement keys into Claude
settings, install the Dependabot entry, link the user-level Codex skill from an updateable
checkout, install the repository ruleset after confirmation, and copy and link the
template Project when the repository has none. It SHALL print, but SHALL NOT perform, the
commands or UI steps that require the person's secret value, Codex review-app setting, or
Project workflow choices. Every local write SHALL be idempotent, and unrelated existing
content SHALL be reported rather than overwritten.

#### Scenario: Fresh repository
- **WHEN** `init` runs in a repository without the process and the person confirms its remote writes
- **THEN** the closed local footprint exists, the ruleset and linked Project exist, and the remaining person-owned actions are printed without reading a secret value

#### Scenario: Second run
- **WHEN** `init` runs again at the same process version
- **THEN** no file, ruleset, Project, setting, or link is duplicated

#### Scenario: Consumer-owned file
- **WHEN** an installation target contains unrelated consumer content that cannot be merged by the target's declared rule
- **THEN** `init` reports the conflict and leaves that content unchanged

### Requirement: The procedure is one skill for both carriers
The artifact rules, architect review, delivery sequence, and install procedure SHALL live
in one `agent-process` skill with its standalone scripts. The Claude plugin SHALL expose
that skill, and Codex SHALL discover the same skill directory through a user-level link.
`openspec/config.yaml` SHALL retain project context and point each artifact rule at the
matching skill section rather than copy the procedure.

#### Scenario: Rule change
- **WHEN** a procedure rule changes in a new release
- **THEN** the publisher changes the shared skill once and an installed consumer receives it by updating the plugin or linked checkout without merging a copied rule body

### Requirement: An update is a version bump, never a process-file merge
A consumer SHALL update the process through the Claude plugin update, the Codex skill
checkout update, and the Dependabot bump of GitHub Action references. No process script,
hook, review contract, or procedure body SHALL be vendored into the consumer repository.

#### Scenario: New release
- **WHEN** a new process tag is published
- **THEN** Dependabot proposes the caller update and the agent-native update paths expose the matching skill version
