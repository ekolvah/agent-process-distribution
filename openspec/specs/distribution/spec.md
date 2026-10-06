# distribution Specification

## Purpose
How the agent process reaches a consumer project and this repository itself, and what
footprint it leaves there.

## Requirements

### Requirement: This repository dogfoods its own process
This repository SHALL expose the shared Claude plugin/skill package that its installer installs
in consumers, and its `.claude/settings.json` SHALL declare the marketplace and enable no plugin,
as a consumer's does. Repository sessions and publisher tests SHALL exercise the
shared skill source, its portable scripts, its installer and templates, its OpenSpec rule
pointers, and its package-version identity. Repository-only settings and v1 process files
SHALL NOT be represented as part of the portable package.

#### Scenario: Process change
- **WHEN** the shared procedure, a portable script, the installer or a template, a rule pointer, or package metadata changes
- **THEN** this repository's own sessions and publisher tests exercise the changed package source while its delivery gates remain intact

#### Scenario: Repository settings
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** it declares `agent-process-marketplace`, runs the skill check at session start, and has no `enabledPlugins` entry for `agent-process@agent-process-marketplace`

### Requirement: The installed footprint is closed
A confirmed installer run SHALL change only the pinned OpenSpec output, the marker-owned
block of `openspec/config.yaml`, the managed `.github/workflows/agent-process.yml`, the
managed `.github/workflows/agent-review.yml`, one marker-owned Dependabot entry, the
marker-owned block of `.pre-commit-config.yaml` — the whole file when the run creates it —, the
seeded `.github/agent-process-quality.json`, the skill
check `.claude/agent-process-check.py`, in `.claude/settings.json` the
`agent-process-marketplace` entry of `extraKnownMarketplaces`, one `hooks.SessionStart` entry
that runs the skill check, and the removal of an `enabledPlugins` entry for
`agent-process@agent-process-marketplace` that is `true`, and, outside the working tree, the
pre-push hook of this clone that `pre-commit install --hook-type pre-push` writes. Every other
consumer file, key, and hook entry SHALL keep its content, and no publisher file is copied into
the consumer.

#### Scenario: Fresh repository
- **WHEN** a confirmed run installs into a fresh repository
- **THEN** the changed paths are exactly the pinned OpenSpec output and those eight files, and only the owned marketplace entry and the owned `SessionStart` entry are added, with no `enabledPlugins`

#### Scenario: Installation of another release
- **WHEN** a confirmed run installs into a repository that carries the owned content of another release, including its `enabledPlugins` entry for the plugin, and consumer content beside it, including its own `SessionStart` hooks and another plugin's `enabledPlugins` entry
- **THEN** only the owned block, files, marketplace entry, and hook entry change, the plugin's `enabledPlugins` entry is removed, and every consumer byte outside them is identical

### Requirement: Init previews the requested release
`init --dry-run` SHALL print the plan of the requested release, one line per transition
marked `planned`, `unchanged`, or `conflict`, and SHALL leave no persistent state in the
consumer repository or the user profile. When the requested version differs from the
running installer's, the plan, its output, and its exit code SHALL come from the requested
release's own installer, run from a temporary checkout that is removed afterwards.

#### Scenario: Dry-run of another version
- **WHEN** an installer of one version runs `--dry-run --version` of another version
- **THEN** the output and exit code are the requested release's own dry-run, and the consumer repository and user profile are byte-identical before and after

### Requirement: Confirmation selects the release first
`init --confirm` of a version other than the running installer's SHALL run the requested
release's installer from a temporary checkout of its tag, removed afterwards, before it writes
any consumer file, and the consumer files SHALL be composed by that release's installer from
that release's templates. The running installer SHALL write nothing in the user profile.

#### Scenario: Confirmed upgrade
- **WHEN** an installer of one version runs `--confirm --version` of another version
- **THEN** every consumer write comes from the requested release's installer, and its temporary checkout no longer exists afterwards

#### Scenario: Confirmed install of the running release
- **WHEN** an installer runs `--confirm` of its own version
- **THEN** the user profile is byte-identical before and after

### Requirement: Init reconciles from observable state
Each transition SHALL be decided from the state it observes, so a rerun of the same version
writes nothing and a retry after an interrupted run performs every unfinished transition
exactly once and no completed one again.

#### Scenario: Retry after an interrupted write
- **WHEN** a confirmed run stops after any one of its persistent writes and is run again
- **THEN** the retry reports each completed transition `unchanged`, performs each unfinished one once, and ends in the same state as an uninterrupted run

### Requirement: Init fails closed on inputs it does not own
A target the installer does not own — a consumer-owned file or key, or malformed ownership
markers — SHALL be reported as `conflict` and the run SHALL exit non-zero before it writes
any consumer file.

#### Scenario: Target the installer does not own
- **WHEN** a dry-run or confirmed run meets a target the installer does not own
- **THEN** it prints `conflict` for that target, exits non-zero, and no consumer file has changed

### Requirement: Init's remote writes are the Project and the installation PR
A confirmed run's only GitHub writes SHALL be one copy of the template Project, one link of a
Project to the repository, and the writes of *Init opens the installation PR*: one issue, one push
of the installation branch, one PR, and, in a repository with no commits, one push of a commit
with no files to the default branch. The installer SHALL NOT create, update, or delete a ruleset,
branch protection, required check, secret, Project field or Status, or a workflow on the default
branch, and SHALL NOT otherwise commit to or push the default branch. A dry-run SHALL issue no
GitHub write and SHALL make no branch, commit, or push.

#### Scenario: Confirmed run
- **WHEN** a confirmed run completes in a repository with commits
- **THEN** every GitHub command it issued is a read, the Project copy, the Project link, the issue creation, or the PR creation, its only push is of the installation branch, and the default branch is unchanged locally and on `origin`

#### Scenario: Dry-run
- **WHEN** a dry-run completes
- **THEN** every GitHub command it issued is a read, and the consumer repository has no new branch, commit, or push

### Requirement: Init provisions one linked Project
A confirmed run SHALL end with exactly one Project linked to the repository. It SHALL reuse
a Project already linked; otherwise reuse the one open, unlinked Project of the repository's
owner titled `<repository name> agent process`; otherwise copy the template Project under
that title; and then link it. Several linked Projects, several such candidates, or a
same-titled Project that is closed or linked elsewhere when no candidate is reusable SHALL be
reported as `conflict`, and the run SHALL exit non-zero before its first write.

#### Scenario: No Project yet
- **WHEN** a confirmed run meets a repository with no linked Project and no same-titled Project of its owner
- **THEN** it copies the template once under the repository's title and links that copy

#### Scenario: Unlinked copy exists
- **WHEN** no Project is linked and exactly one open, unlinked same-titled Project exists
- **THEN** the run links it and copies nothing

#### Scenario: Ambiguous Projects
- **WHEN** several Projects are linked, several same-titled candidates exist, or the only same-titled Project is closed or linked elsewhere
- **THEN** a dry-run or confirmed run prints `conflict` naming them, exits non-zero, and has written nothing locally or remotely

### Requirement: Project provisioning is recoverable
A retry after a copy or link that failed, or that took effect while its command reported
failure, SHALL decide from the observed Projects and SHALL NOT create a second copy.

#### Scenario: Link failed after the copy
- **WHEN** the copy succeeds, the link fails, and the run is repeated
- **THEN** across both runs the template is copied once and the link is attempted twice, and the copy ends linked

#### Scenario: Link output lost
- **WHEN** the link takes effect but its command reports failure, and the run is repeated
- **THEN** the retry reports the Project linked as `unchanged` and issues no copy and no link

### Requirement: Project UI actions are printed, not performed
A run SHALL print, as `manual`, setting the Project's visibility while the linked Project is
private, enabling the template's built-in workflows the linked Project lacks or has disabled —
naming only those — and replacing the `Area` options and area views with the consumer's own
while the linked Project's `Area` options equal the template's; and `init` SHALL issue no
command that changes any of them.

#### Scenario: Manual actions
- **WHEN** a confirmed run completes after copying and linking the template Project
- **THEN** its output carries the three `manual` rows, the workflows row names `Auto-add to project` and no other workflow, and no command it issued changes a Project's visibility, workflows, fields or views

### Requirement: The quality callee runs the declared commands
The reusable workflow `quality.yml` SHALL take no input and SHALL read `setup`, `test` and
`checks` from `.github/agent-process-quality.json` of the PR's checkout. A job SHALL verify
that the PR links its issue. When `checks` is declared, its output SHALL be a JSON array of
check names, and each name SHALL run `setup` when one is declared and then `test --only <name>`
on the PR's checkout, in a job of its own named after the check. A failing check job SHALL NOT
cancel another. Without `checks`, one job SHALL run `setup` and then `test`. When the file is
absent, the run SHALL execute no command of the PR and SHALL show a warning annotation saying
that no quality command is declared and the run tests nothing. A declaration that is not valid
JSON, is not an object, holds a `test` that is missing, blank or not a string, a `setup` or
`checks` that is not a string, or a value with a line break, SHALL fail the run with an error
naming the fault. The job
`quality` SHALL succeed only when the link job, the listing job, and every check job succeeded,
and SHALL fail otherwise, including when one of them was skipped or cancelled.

#### Scenario: Consumer test fails
- **WHEN** the declared `test` exits non-zero on a PR that links its issue
- **THEN** the `quality` job fails

#### Scenario: One check fails
- **WHEN** the declaration gives `checks`, and on a PR that links its issue one listed check exits non-zero
- **THEN** that check's job fails, every other listed check's job runs to its own conclusion, and the `quality` job fails

#### Scenario: Listing fails
- **WHEN** the declared `checks` command exits non-zero or prints anything but a non-empty JSON array of check names
- **THEN** the `quality` job fails

#### Scenario: No declaration
- **WHEN** a PR that links its issue has no `.github/agent-process-quality.json`
- **THEN** the run shows a warning annotation that no quality command is declared, runs no command of the PR, and the `quality` job succeeds

#### Scenario: Malformed declaration
- **WHEN** the declaration is not a JSON object with a non-blank string `test`, its `setup` or `checks` is not a string, or a value holds a line break
- **THEN** the run fails with an error naming the declaration file and the fault

### Requirement: Callers reach the quality callee
A caller job of `quality.yml` SHALL be named `agent-process`, so the check reports as
`agent-process / quality`, and SHALL pass no input. A consumer caller SHALL call it at an
immutable release tag `@v<version>`. The publisher caller SHALL call it by a same-repository
`./` path, which takes caller and callee from the same commit.

#### Scenario: Consumer render
- **WHEN** the installer renders the managed caller for release `<version>`
- **THEN** its one job `agent-process` calls `ekolvah/agent-process-distribution/.github/workflows/quality.yml@v<version>` with no input

#### Scenario: Publisher PR
- **WHEN** a PR of this repository runs its workflows
- **THEN** `agent-process / quality` runs `python .agent-process/scripts/ci_check.py` from the callee at the PR's own commit

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

### Requirement: Activation previews every remote write
A run SHALL print one line per ruleset transition, marked `planned`, `unchanged`, or
`conflict`. A rollback command SHALL follow each `planned` line. The run SHALL print the
required contexts of classic branch protection as read. A dry-run SHALL issue only GitHub
reads.

#### Scenario: Dry-run
- **WHEN** a dry-run completes on a repository whose ruleset differs from the process ruleset
- **THEN** it prints the `planned` update and its rollback command, prints the classic protection read, and every GitHub command it issued is a read

### Requirement: Activation converges one ruleset
A confirmed run SHALL leave exactly one repository ruleset named `agent-process default
branch`. It SHALL create that ruleset when none exists. It SHALL update the ruleset in place
when an owned field differs, and write nothing when all owned fields are equal. Several
rulesets with that name, or one whose source is not the repository, SHALL be a `conflict`,
and the run SHALL exit non-zero before its first write. The run SHALL NOT write classic
branch protection.

#### Scenario: No ruleset yet
- **WHEN** a confirmed run meets a repository with no ruleset of that name
- **THEN** it creates one ruleset and writes nothing else

#### Scenario: Live ruleset differs
- **WHEN** the one ruleset of that name requires another context
- **THEN** a confirmed run updates that ruleset under the same ID and creates none

#### Scenario: Rerun
- **WHEN** a confirmed run is repeated after it succeeded
- **THEN** it reports the ruleset `unchanged` and issues no write

#### Scenario: Ambiguous rulesets
- **WHEN** two rulesets carry the process name, or the one that does is not repository-owned
- **THEN** a dry-run or confirmed run prints `conflict` naming them, exits non-zero, and has issued no write

### Requirement: Activation reads back what it wrote
After a write, the run SHALL read the ruleset back and SHALL exit non-zero on the first
field that differs, and name it. The checked fields are the default-branch ref, active
enforcement, the pull request, deletion, and non-fast-forward rules, the empty bypass list,
the strict policy, and the exact set of required contexts, each with its integration ID, in
any order.

#### Scenario: Read-back mismatch
- **WHEN** the ruleset read after a write lacks a barrier rule, has a bypass actor, requires another context or integration, or lacks or adds a context
- **THEN** the run exits non-zero and names that field

#### Scenario: Read-back reorders contexts
- **WHEN** the ruleset read after a write returns the written contexts in another order
- **THEN** the read-back passes, and a later dry-run prints `unchanged`

### Requirement: A context the PR cannot change gates every head
Every head of this repository SHALL be gated by a required context that the PR cannot
change: `agent-review / agent-review`, which reviews that head. A required context that runs
the PR's own driver, `agent-process / quality`, SHALL be required only beside it. Each PR
SHALL run each check of the quality driver once.

#### Scenario: PR weakens its own driver
- **WHEN** a PR of this repository changes the driver that `agent-process / quality` runs
- **THEN** the contexts the repository declares required for that head still include `agent-review / agent-review`

#### Scenario: Quality runs once per PR
- **WHEN** a PR of this repository opens or receives a push
- **THEN** only jobs of the `agent-process` caller execute the quality driver on its head, and each check of its registry runs in exactly one of them

### Requirement: Package paths resolve in a consumer
A file of the package — the skill directory, `agents/`, and `commands/` — SHALL NOT name a
path under the publisher's `.agent-process/` root, and no relative Markdown link of a skill
file SHALL leave the skill directory. The principles the architect review applies SHALL be a
file of the skill directory. A plugin agent SHALL name each package file by its path in the
skill directory, from the repository root, and SHALL name `${CLAUDE_PLUGIN_ROOT}` as the root
where the repository has no skill directory.

#### Scenario: Publisher-only path in the package
- **WHEN** a package file names a `.agent-process/` path, a skill file links a relative target outside the skill directory, or a plugin agent names a path in the skill directory that is not a package file or names no `${CLAUDE_PLUGIN_ROOT}` fallback
- **THEN** the publisher tests fail and name that file and path

### Requirement: A Claude session start reports a missing skill
The installed skill check SHALL read `claude plugin list --json`. When an enabled install of
`agent-process@agent-process-marketplace` of a scope other than user has a project path equal to
the project directory ignoring case, it SHALL exit 0 with a `systemMessage` for the person naming
`agent-process project-scope install applies`, the Install URL the hook passes it, and, for each
such install, its version and the command that removes it: `cd /d "<projectPath>"` (a path with a
drive letter) or `cd "<projectPath>"` (any other path) with the install's exact `projectPath`
spelling, followed by `&& claude plugin uninstall agent-process@agent-process-marketplace --scope
<its scope>`; and an `additionalContext` telling the agent to tell the person. Otherwise it SHALL
pass silently only when exactly one enabled user-scope install exists and it holds
`skills/agent-process/SKILL.md`. In every other case, including a missing or failing CLI,
unparsable output, or an error of the check itself, it SHALL exit 0 with a `systemMessage` for the
person naming `agent-process skill not loaded`, the reason, and the Install URL (the Install
section of the installed release's skill), and an `additionalContext` telling the agent not to
reconstruct the skill; when no enabled user-scope install exists, the reason SHALL name `claude
plugin install agent-process@agent-process-marketplace`.

#### Scenario: Skill loaded
- **WHEN** exactly one enabled user-scope install holds the skill and no other-scope install applies to the project
- **THEN** the check prints nothing and exits 0

#### Scenario: Project-scope install applies
- **WHEN** a user-scope install and two project-scope installs of the project whose `projectPath` differs only in drive-letter case are listed
- **THEN** the output names `agent-process project-scope install applies`, not `agent-process skill not loaded`, the Install URL, and for each project-scope install `cd /d "<its projectPath>" && claude plugin uninstall agent-process@agent-process-marketplace --scope project` with that install's spelling

#### Scenario: Skill not loaded
- **WHEN** no enabled user-scope install exists, several distinct ones exist, or the one that exists lacks `skills/agent-process/SKILL.md`
- **THEN** the check exits 0 and its output names `agent-process skill not loaded`, the reason, and the Install URL, to the person and to the agent, and a missing user-scope install's reason names `claude plugin install agent-process@agent-process-marketplace`

#### Scenario: Check cannot decide
- **WHEN** the `claude` CLI is missing, exits non-zero, prints output that is not the expected JSON, or the check raises
- **THEN** the check exits 0 with the `agent-process skill not loaded` marker naming that reason

### Requirement: Delivery entry scripts refuse release drift
The installer SHALL record the installed release as the line `# agent-process release: <version>`
in its `openspec/config.yaml` block. `create_tracking_issue` and `start_change` SHALL read that
line before any other step and, when it is absent, not a `<major>.<minor>.<patch>` version, or
different from the release of the running skill, exit 2 without a GitHub call, naming both
releases and the fix: re-run Install with the running skill when the project's release is absent,
unparsable or older, or `claude plugin update agent-process@agent-process-marketplace` with the
install's scope and a session restart when the skill's release is older, never a marketplace ref pinned to a release
tag. Scripts run from `skills/agent-process/scripts` under the repository root SHALL skip the
comparison.

#### Scenario: Release recorded
- **WHEN** a confirmed installer run writes the `openspec/config.yaml` block
- **THEN** the block holds `# agent-process release: <version>` of the installed release

#### Scenario: Release drift
- **WHEN** `create_tracking_issue` or `start_change` runs from a skill outside the repository's `skills/agent-process/scripts` and the recorded release is absent, unparsable, older or newer than the skill's
- **THEN** it exits 2 before any GitHub call, and its message names both releases and the fix for that direction

#### Scenario: Publisher checkout
- **WHEN** either script runs from `<root>/skills/agent-process/scripts` of a repository whose config records no release
- **THEN** it proceeds past the comparison

### Requirement: Releases go through release-please
A release SHALL be cut by `release-please` alone: on a push to `main` it SHALL open or
update one release PR whose version follows the Conventional Commit types on `main` since the
last release, and that PR SHALL move every version place — `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `VERSION` in `skills/agent-process/scripts/init.py` and
the release manifest — to that version in one commit. The release PR SHALL be opened with a
token whose events start workflows, so the required contexts run on it. The release workflow
SHALL enable auto-merge with squash on the PR it opened or updated, with the same token, and
the repository SHALL allow auto-merge; a failure to enable it SHALL fail the workflow run. A
run that opens or updates no release PR SHALL succeed without enabling auto-merge.
Merging the release PR SHALL create the tag `v<version>` and its GitHub Release; no person or
script sets a release tag by hand.

#### Scenario: Version places agree
- **WHEN** the tests run on any head, including a release PR's
- **THEN** every version place equals the version of the release manifest, and the release-please configuration names each place

#### Scenario: Release PR opened or updated
- **WHEN** the release workflow opens or updates the release PR
- **THEN** auto-merge with squash is enabled on that PR, or the workflow run fails

#### Scenario: No release PR change
- **WHEN** the release workflow runs and opens or updates no release PR
- **THEN** the workflow run succeeds and the auto-merge step is skipped

#### Scenario: Release PR merged
- **WHEN** the release PR of version `<version>` merges once its required checks pass
- **THEN** the tag `v<version>` and a GitHub Release of that tag exist on the merge commit

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
A run SHALL print, as `manual`, setting the repository secret `CLAUDE_CODE_OAUTH_TOKEN` while
the repository's secret names do not include it, and `init` SHALL issue no command that writes
a secret. The row SHALL name the repository's Actions secrets page and give the commands
`claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>`, with the
consumer repository substituted.

#### Scenario: Review prerequisites
- **WHEN** a dry-run or confirmed run completes on a repository without the secret
- **THEN** its output carries one `manual` row for the secret naming that repository's Actions secrets page, `claude setup-token` and `gh secret set CLAUDE_CODE_OAUTH_TOKEN -R <owner/repo>` of that repository, and no command it issued writes a secret

### Requirement: The marketplace follows the stable channel
The installer SHALL render the `agent-process-marketplace` declaration of
`.claude/settings.json` with the source `ref` `stable` and `"autoUpdate": true`, for every
release. A run SHALL print, as `manual`, the once-per-machine step that declares the
marketplace at `stable` in user settings, enables its auto-update, and installs the plugin at
user scope, while the machine's known marketplace is not at `stable` with auto-update or the
plugin has no user-scope install, and `init` SHALL issue no command that changes plugin or
marketplace state.

#### Scenario: Channel render
- **WHEN** the installer renders the settings of any release
- **THEN** the marketplace source's `ref` is `stable` and the marketplace entry's `autoUpdate` is `true`

#### Scenario: Machine channel step
- **WHEN** a dry-run or confirmed run completes on a machine without the marketplace
- **THEN** its output carries one `manual plugin-channel` row naming `claude plugin marketplace add "ekolvah/agent-process-distribution#stable"`, enabling auto-update, and `claude plugin install agent-process@agent-process-marketplace`, and no command it issued is a `claude` command

### Requirement: A release moves the stable channel
When the release workflow creates a release, it SHALL fast-forward the branch `stable` to the
commit that release tagged, with the token that tagged it. A failed or non-fast-forward update
SHALL fail the workflow run. A run that creates no release SHALL NOT change `stable`.

#### Scenario: Release created
- **WHEN** the release workflow creates the release of version `<version>`
- **THEN** it updates `refs/heads/stable` to the tagged commit without force, and a refused update fails the run

#### Scenario: No release
- **WHEN** the release workflow runs and creates no release
- **THEN** the `stable` update step is skipped

### Requirement: Dependabot leaves process refs to Install
The installer's marker-owned Dependabot entry SHALL ignore every dependency named
`ekolvah/agent-process-distribution` or under it.

#### Scenario: Dependabot render
- **WHEN** the installer writes its Dependabot entry
- **THEN** the `github-actions` entry ignores the dependency name pattern `ekolvah/agent-process-distribution*`

### Requirement: Skill commands run from a consumer root
Every script command a skill file prints SHALL be `agent-process <script>` followed by its
arguments, naming a script of the skill directory. The plugin SHALL ship `agent-process` as an
executable of its `bin/`, which SHALL run `python <script>.py` with the remaining arguments from
`skills/agent-process/scripts/` of the current directory when that file exists there, otherwise
from the plugin's own skill directory, and SHALL propagate the script's exit code. A missing or
unknown script name SHALL exit 2 naming the available scripts.

#### Scenario: Printed command in a consumer
- **WHEN** a command printed by a skill file runs through `agent-process` from a directory that has no `skills/agent-process/`
- **THEN** the named script of the plugin's skill directory runs with the printed arguments and its exit code is the command's

#### Scenario: Publisher checkout runs its own scripts
- **WHEN** `agent-process <script>` runs from a directory whose `skills/agent-process/scripts/<script>.py` exists
- **THEN** that file runs, not the plugin's copy

#### Scenario: Unknown script
- **WHEN** `agent-process` runs without a script name or with a name that is not a script of the skill directory
- **THEN** it exits 2 naming the available scripts and runs nothing

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

### Requirement: Init asks for no quality command
`init` SHALL take no test or setup command. The quality commands of a repository SHALL live in
its own declaration `.github/agent-process-quality.json`, a JSON object with a non-blank string
`test` and optional string `setup` and `checks`, each on one line. When the declaration is
absent and the run creates `.pre-commit-config.yaml`, the run SHALL classify a `quality`
transition, printed before the `pre-commit` transition, whose write seeds the declaration with a
`setup` that installs `pre-commit` and `pytest` at this repository's pins and then each of
`requirements.txt` and `requirements-dev.txt` that exists, failing when an install fails, and the `test`
`pre-commit run --hook-stage manual --all-files --show-diff-on-failure`. `init` SHALL write the
declaration in no other case and SHALL never change an existing one; while it exists, the run
SHALL print the `quality` transition `unchanged`. While the declaration is
absent or declares no valid `test` and the run plans no `quality` transition, the output of a
dry-run and of a confirmed run SHALL carry, before the `manual` rows, one status line starting
`quality: ` that names the declaration and says CI runs no tests until the declaration exists,
and no `manual` row about it. An existing
managed caller that passes a `test` input while the declaration declares no `test` SHALL be
reported as `conflict` naming that input, and the run SHALL exit non-zero before any write.

#### Scenario: Fresh install seeds the declaration
- **WHEN** a dry-run and then a confirmed run meet a repository with neither `.github/agent-process-quality.json` nor `.pre-commit-config.yaml`
- **THEN** the dry-run prints `planned quality` before `planned pre-commit` and writes nothing, the confirmed run writes the declaration with that `setup` and `test`, and neither output carries a `quality: ` line

#### Scenario: Install without tests
- **WHEN** a dry-run or confirmed run meets a repository with `.pre-commit-config.yaml` and without `.github/agent-process-quality.json`
- **THEN** it prints no `quality` transition, its output carries one `quality: ` line naming the declaration before any `manual` row and no `manual quality-command` row, and a confirmed run writes no declaration

#### Scenario: Declared quality command
- **WHEN** a dry-run or confirmed run meets a valid declaration of a `test`
- **THEN** its output carries `unchanged quality` and no `quality: ` line, and the declaration keeps its bytes

#### Scenario: Upgrade over a passed test command
- **WHEN** a run meets a managed caller that passes a `test` input and no declaration of a `test`
- **THEN** it prints `conflict` naming the passed command and the declaration file, exits non-zero, and no consumer file has changed

### Requirement: Init opens the installation PR
When a confirmed run changes a consumer file, it SHALL make the change on the branch
`agent-process/install-<version>` created from the default branch, commit it there, push that
branch to `origin`, and open one PR from it to the default branch whose body starts
`Closes #<N>`, where `<N>` is the open issue titled `Install agent-process <version>`, created only
when none is open. In a repository with no commits, it SHALL first push one commit with no files
to the default branch that the repository's settings name, and create the installation branch
from that commit. The written PR line SHALL name the PR's URL. A run that would change a consumer
file from a worktree with changes, from a branch other than the default or the installation
branch, while the installation branch exists but is not checked out, from a checkout with commits
of a repository with none, or from a checkout with no commits of a repository with commits, or on
the installation branch whose only PR was closed unmerged SHALL report `conflict` naming the
cause, before any write; no conflict line SHALL name an empty branch. A run that changes no
consumer file on the default branch, or runs on the installation branch after its PR is merged,
SHALL make no branch, commit, issue, push, or PR.

#### Scenario: Fresh install opens the PR
- **WHEN** a confirmed run installs from the clean default branch of a repository with no such issue
- **THEN** `origin` has the installation branch one commit ahead of the default branch carrying exactly the installer's changes, one open PR from it whose body starts `Closes #<N>` for the new open issue `Install agent-process <version>`, and the output names that PR

#### Scenario: Repository with no commits
- **WHEN** a dry-run and then a confirmed run install from a clean clone of a repository with no commits
- **THEN** the dry-run prints `planned onboarding-root` and writes nothing, and after the confirmed run the default branch on `origin` is one commit with no files and no parent, the installation branch is one commit ahead of it carrying exactly the installer's changes, and one open PR goes from it to the default branch

#### Scenario: Open issue is reused
- **WHEN** an open issue titled `Install agent-process <version>` exists before a confirmed run
- **THEN** the PR body starts `Closes #<N>` for that issue and no issue is created

#### Scenario: Nothing to install
- **WHEN** a confirmed run on the default branch changes no consumer file
- **THEN** it creates no branch, commit, issue, push, or PR

#### Scenario: Rerun after the merge
- **WHEN** a confirmed run is on the installation branch and its PR is merged
- **THEN** it reports each onboarding transition `unchanged` naming the merged PR, and creates no issue, push, or PR

#### Scenario: Unsafe starting point
- **WHEN** a run would change a consumer file from a worktree with changes, from another branch, while the installation branch exists but is not checked out, from a checkout with commits of a repository with none, or from a checkout with no commits of a repository with commits, or runs on the installation branch whose only PR was closed unmerged
- **THEN** it prints `conflict` naming the cause and no empty branch name, exits non-zero, and has made no write

### Requirement: A push runs the declared test
The pre-commit hook `quality` that this repository's `.pre-commit-hooks.yaml` declares SHALL run
at `pre-push` the `test` that `.github/agent-process-quality.json` of the pushed checkout
declares, once, through `bash`, with the names that `git rev-parse --local-env-vars` prints
and the environment pre-commit built for the hook removed from its environment, and SHALL exit
with that command's exit code. It SHALL run no
`setup` and no `checks`. Without the file it SHALL print that no quality command is declared and
the push checked nothing, and exit 0. A malformed declaration SHALL fail with an error naming the
fault. When `bash` or the git environment names cannot be found it SHALL exit 2 naming the
cause. This repository's `.pre-commit-config.yaml` SHALL run the same entry from its own commit.

#### Scenario: Declared test fails
- **WHEN** the declared `test` exits non-zero
- **THEN** the hook exits with that code and the push is refused

#### Scenario: No declaration
- **WHEN** the pushed checkout has no `.github/agent-process-quality.json`
- **THEN** the hook prints that no quality command is declared and exits 0

#### Scenario: Push from a linked worktree
- **WHEN** the hook runs with `GIT_DIR` and `GIT_INDEX_FILE` set
- **THEN** the declared `test` sees neither

#### Scenario: Declared test runs python
- **WHEN** pre-commit runs the hook and the declared `test` runs `python`
- **THEN** that is the interpreter the pusher's `PATH` names, not the hook's environment

#### Scenario: This repository's push
- **WHEN** this repository's `.pre-commit-config.yaml` is read
- **THEN** its hook `quality` runs `skills/agent-process/scripts/quality.py --hook` at `pre-push`

### Requirement: Init renders the pre-push hook
The owned block of `.pre-commit-config.yaml` SHALL reference the hook `quality` of
`https://github.com/ekolvah/agent-process-distribution` at `rev: v<version>`, and a file the run
creates SHALL also set `default_install_hook_types: [pre-push]`. An existing file without the
block SHALL be reported as `conflict`. A run SHALL classify a `pre-push` transition, printed
after every onboarding transition: `unchanged` while this clone has `core.hooksPath` unset and a
pre-push hook that pre-commit installed, otherwise `planned` when `core.hooksPath` is unset and
`pre-commit` is on `PATH`. A confirmed run SHALL perform it after the installation PR by running
`pre-commit install --hook-type pre-push` in the clone, and SHALL fail with exit 1 when the hook
it then reads is not one pre-commit installed. A planned `pre-push` transition alone SHALL NOT
make a branch, commit, issue, push, or PR. When this clone has `core.hooksPath` set or
`pre-commit` is not on `PATH`, the run SHALL print no `pre-push` transition and SHALL print a
`manual pre-push` row naming that reason, `git config --unset-all core.hooksPath` where it is
set, and then `pre-commit install --hook-type pre-push`.

#### Scenario: Consumer render
- **WHEN** a confirmed run installs release `<version>`
- **THEN** `.pre-commit-config.yaml` references the hook `quality` at `rev: v<version>`, and pre-commit runs it at `pre-push`

#### Scenario: Consumer file without the block
- **WHEN** a run meets a `.pre-commit-config.yaml` without an agent-process block
- **THEN** it prints `conflict` for that file, exits non-zero, and no consumer file has changed

#### Scenario: Hook installed in this clone
- **WHEN** a dry-run and then a confirmed run complete in a clone without a pre-push hook, with `core.hooksPath` unset and `pre-commit` on `PATH`
- **THEN** the dry-run prints `planned pre-push` and leaves the clone without a hook, the confirmed run prints `written pre-push` after `onboarding-pr` and leaves a hook that pre-commit installed, and neither prints a `manual pre-push` row

#### Scenario: Install leaves no hook
- **WHEN** a confirmed run's `pre-commit install --hook-type pre-push` exits 0 but leaves no hook that pre-commit installed
- **THEN** the run prints no `written pre-push`, names the hook path, and exits 1

#### Scenario: Hook missing where nothing else is planned
- **WHEN** a confirmed run on the default branch changes no consumer file in a clone without a pre-push hook, with `core.hooksPath` unset and `pre-commit` on `PATH`
- **THEN** it prints `written pre-push`, and creates no branch, commit, issue, push, or PR

#### Scenario: Per-clone row
- **WHEN** a dry-run or confirmed run completes in a clone that has `core.hooksPath` set, or where `pre-commit` is not on `PATH`
- **THEN** it prints no `pre-push` transition, writes no hook, and its output carries one `manual pre-push` row naming that reason and both commands

### Requirement: Manual rows follow observed state
A dry-run and a confirmed run SHALL end their output with the `manual` rows, classified after
the run's writes from reads that write nothing, and SHALL omit a row whose target state is
observed. A row whose state `init` cannot read SHALL be printed with `(cannot read: <reason>)`,
and a failed read SHALL NOT change the run's exit code.

#### Scenario: Observed done
- **WHEN** a run meets the secret `CLAUDE_CODE_OAUTH_TOKEN` set, the marketplace at `stable` with auto-update and the plugin installed at user scope, this clone's pre-push hook installed by pre-commit, and a linked public Project with the required workflows enabled and Area options other than the template's
- **THEN** its output carries no `manual` row

#### Scenario: Unreadable state
- **WHEN** the read of the secret names fails, or a machine plugin file is not the JSON shape `init` reads
- **THEN** the run exits as it would otherwise, and the row of that state is printed with `(cannot read: <reason>)`

### Requirement: A Claude session start reports a missing pre-push hook
When the project directory's `.pre-commit-config.yaml` carries the line `# agent-process:begin`
and this clone has `core.hooksPath` set or has no pre-push hook that pre-commit installed, the
installed skill check SHALL exit 0 with a `systemMessage` for the person and an
`additionalContext` for the agent, each naming `agent-process pre-push hook not installed`, the
reason, `git config --unset-all core.hooksPath` where it is set, and
`pre-commit install --hook-type pre-push`. A state it cannot read SHALL print the same marker
naming that reason. Without that line, or with the hook installed, it SHALL add nothing for the
hook; a skill marker it prints SHALL stay in the same output.

#### Scenario: Hook missing
- **WHEN** a Claude session starts in a clone whose `.pre-commit-config.yaml` carries the agent-process block and that has no pre-push hook pre-commit installed, or has `core.hooksPath` set
- **THEN** the check exits 0 and its output names `agent-process pre-push hook not installed`, the reason, and both commands, to the person and to the agent

#### Scenario: Hook installed or not rendered
- **WHEN** the skill is loaded and the clone's `.pre-commit-config.yaml` has no agent-process block, or the clone runs pre-commit's pre-push hook
- **THEN** the check prints nothing and exits 0

#### Scenario: Hook state unreadable
- **WHEN** the check cannot read `.pre-commit-config.yaml`, the git config, or the hook path
- **THEN** the check exits 0 with the `agent-process pre-push hook not installed` marker naming that reason

### Requirement: Init names a failed command's output
When a command `init` runs exits non-zero, the error SHALL name every non-empty captured stream,
stderr before stdout. When neither stream was captured, it SHALL say `output not captured`.

#### Scenario: Output on both streams
- **WHEN** a command exits 1 with text on stderr and different text on stdout
- **THEN** the error names the exit code and both texts, stderr first

#### Scenario: Output not captured
- **WHEN** a command exits 1 and neither of its streams was captured
- **THEN** the error says `output not captured`

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
Every tool hook command of the plugin SHALL exit 0 with no output when the session's project
directory has no `.github/workflows/agent-process.yml`. The `SessionStart` environment install
is not gated: `init` and the first propose run of a consumer can share one session.

#### Scenario: Unadopted repository
- **WHEN** any tool hook command of the plugin runs with a project directory that has no `.github/workflows/agent-process.yml`, for an input its policy would deny
- **THEN** it exits 0 with empty stdout

### Requirement: The plugin ships the memory checkpoint
After an `Edit` or `Write` of a file under the agent's auto-memory directory
(`.claude/projects/<project>/memory/`), the plugin's hook SHALL show the agent a reminder
without undoing the write. The reminder SHALL name the file and ask whether every session and
every person working on the repository needs the fact; if so, it SHALL ask the agent to move
the fact into the repository. Any
other path SHALL produce no output. This repository's `.claude/settings.json` SHALL declare no
post-edit hook of its own.

#### Scenario: Memory write in an adopted consumer
- **WHEN** the plugin's `PostToolUse` hook runs with a project directory that carries `.github/workflows/agent-process.yml` and no copy of the check, for a `Write` of a file under `.claude/projects/<project>/memory/` given with either path separator
- **THEN** it exits 2 with stderr naming the file, asking whether every session and every person needs the fact, and if so to move it into the repository

#### Scenario: Write outside auto-memory
- **WHEN** the same hook runs for a file of the repository, including one under `.claude/rules/`, or for a payload without a file path
- **THEN** it exits 0 with no output

#### Scenario: Repository hook carries no memory check
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** it declares no `PostToolUse` hook, so the plugin's checkpoint is the only memory check

### Requirement: The plugin ships edit-time lint
After an `Edit` or `Write`, the plugin's hook SHALL run `pre-commit run --hook-stage pre-commit
--files <edited path>` in the session's project directory and SHALL show the agent that run's
output with exit 2 when the run fails. A run that passes SHALL produce no output. When
`pre-commit` is not on `PATH`, the hook SHALL exit 2 with a marker saying that edit-time lint is
not active. This repository's `.pre-commit-config.yaml` SHALL
declare the `ruff-check` and `ruff-format` hooks of `astral-sh/ruff-pre-commit` at the
`pre-commit` stage as its only pin of ruff, and its `.claude/settings.json` SHALL declare no
`PostToolUse` hook.

#### Scenario: Commit-stage finding
- **WHEN** the plugin's hook runs in an adopted consumer whose `.pre-commit-config.yaml` declares a `pre-commit`-stage hook that fails on the edited file
- **THEN** it exits 2 with stderr carrying that hook's output

#### Scenario: Only pre-push hooks declared
- **WHEN** the same hook runs in an adopted consumer whose `.pre-commit-config.yaml` declares hooks only at the `pre-push` stage
- **THEN** it exits 0 with no output, and no `pre-push` hook runs

#### Scenario: pre-commit missing
- **WHEN** the hook runs with no `pre-commit` on `PATH`
- **THEN** it exits 2 with stderr naming `pre-commit` and saying that edit-time lint is not active

#### Scenario: This repository's edit-time lint
- **WHEN** the publisher tests read this repository's `.pre-commit-config.yaml`, `.agent-process/requirements-dev.in` and `.claude/settings.json`
- **THEN** the config declares `ruff-check` and `ruff-format` of `astral-sh/ruff-pre-commit` at the `pre-commit` stage only, `requirements-dev.in` names no `ruff`, and the settings declare no `PostToolUse` hook

### Requirement: Init seeds the baseline toolchain
A `.pre-commit-config.yaml` that a run creates SHALL set `minimum_pre_commit_version: "4.4.0"`
and SHALL declare, outside the agent-process block, these hooks. At the `pre-commit` and
`manual` stages: `ruff-check` of `astral-sh/ruff-pre-commit` with the rules `C901`, `PLR0911`,
`PLR0912`, `PLR0913` and `PLR0915` added to its selection, `ruff-format` of the same repository,
`mypy` of `pre-commit/mirrors-mypy` with `args: []`, so an import it cannot resolve fails the hook, `pylint` of `pylint-dev/pylint` with only `too-many-lines`
enabled at 1000 lines, and `detect-secrets` of `Yelp/detect-secrets`. At the `manual` stage
only: `pip-audit` of `pypa/pip-audit`, once for `requirements.txt` and once for
`requirements-dev.txt`, each running only while its file is tracked, and a local hook `pytest`
that runs `python -m pytest` of the `python` on `PATH` once, only while a file named
`test_*.py` or `*_test.py` is tracked. Each hook's `rev` SHALL equal this repository's pin of
that tool: ruff the `rev` of this repository's `.pre-commit-config.yaml`, every other tool its
`.agent-process/requirements-dev.txt` line. An existing `.pre-commit-config.yaml` SHALL keep
every byte outside the block.

#### Scenario: Created config
- **WHEN** a confirmed run creates `.pre-commit-config.yaml`
- **THEN** the file declares the agent-process block and those hooks at those stages, and each `rev` equals this repository's pin of its tool

#### Scenario: Tests run once they exist
- **WHEN** `pre-commit run --hook-stage manual --all-files` runs the created config's `pytest` hook in a repository with no tracked test file, and again after a failing `tests/test_a.py` is tracked
- **THEN** the first run reports the hook skipped and exits 0, and the second runs the test and exits non-zero

#### Scenario: Existing config keeps its hooks
- **WHEN** a confirmed run meets a `.pre-commit-config.yaml` with the agent-process block and hooks of the repository's own
- **THEN** every byte outside the block is unchanged and no baseline hook is added

### Requirement: The plugin installs its runtime environment
At session start, the plugin SHALL install its runtime manifest `.agent-process/requirements.txt`
into a virtual environment under `${CLAUDE_PLUGIN_DATA}` named by the manifest's content, when
no completed environment of that name exists or its interpreter fails `pip check`, and SHALL then export `AGENT_PROCESS_PYTHON`, the
environment's interpreter, through `CLAUDE_ENV_FILE`. An install SHALL NOT modify an environment
of another manifest. The launcher SHALL run every script with `AGENT_PROCESS_PYTHON` when it is
set, and with `python` otherwise. A failed install, or a hook run without `CLAUDE_PLUGIN_DATA` or
`CLAUDE_ENV_FILE`, SHALL exit 0 with an `agent-process plugin environment not installed` marker
to the person and to the agent; a failed install SHALL be retried at the next session start.

#### Scenario: First session
- **WHEN** the plugin's `SessionStart` hook runs with an empty data directory
- **THEN** it exits 0 with empty stdout, the environment's interpreter exists, and `CLAUDE_ENV_FILE` exports `AGENT_PROCESS_PYTHON` naming it

#### Scenario: Manifest unchanged
- **WHEN** the hook runs again with the same manifest
- **THEN** it does not reinstall the environment and exports `AGENT_PROCESS_PYTHON` again

#### Scenario: Install fails
- **WHEN** the manifest cannot be installed
- **THEN** the hook exits 0, its output names `agent-process plugin environment not installed` to the person and to the agent, and the next run installs again

#### Scenario: Broken environment
- **WHEN** the hook runs and the completed environment's interpreter cannot run
- **THEN** it reinstalls that environment and exports its interpreter

#### Scenario: Hook variables absent
- **WHEN** the hook runs without `CLAUDE_PLUGIN_DATA` or without `CLAUDE_ENV_FILE`
- **THEN** it exits 0 and its output names `agent-process plugin environment not installed` and the missing variable

#### Scenario: Manifest changed
- **WHEN** the hook runs with a manifest different from the one an existing environment was installed from
- **THEN** it installs a second environment, exports that one, and leaves the first unchanged

#### Scenario: Launcher uses the session interpreter
- **WHEN** `agent-process <script>` runs with `AGENT_PROCESS_PYTHON` set
- **THEN** the script runs under that interpreter

### Requirement: Bare openspec runs the pin
The plugin SHALL ship `openspec` as an executable of its `bin/`, which SHALL run
`npx -y @fission-ai/openspec@<pin>` with all its arguments and propagate the exit code, where
`<pin>` is the OpenSpec version `init` installs. Outside `openspec/changes/`, no tracked file
other than `bin/openspec` SHALL write an OpenSpec version after `@fission-ai/openspec@`.

#### Scenario: Bare command
- **WHEN** `openspec <args>` runs with the plugin's `bin/` on `PATH` and no other `openspec` before it
- **THEN** `npx` runs with `-y @fission-ai/openspec@<pin> <args>`, each argument intact, and its exit code is the command's

#### Scenario: One pin
- **WHEN** the publisher tests read the tracked files outside `openspec/changes/`
- **THEN** `bin/openspec` names `@fission-ai/openspec@<pin>`, and any other file that writes a version after `@fission-ai/openspec@` fails naming the file

### Requirement: The plugin ships the git guard
The plugin's `PreToolUse` hook for the `Bash` tool SHALL deny a command when any of its stages,
including one behind a shell separator, a process wrapper, an environment assignment, `sh -c`,
git's global options or `gh`'s `-R`/`--repo` before the subcommand, is one of:
- `gh pr merge` — the reason SHALL say that the person merges;
- `gh repo delete`;
- `git push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes`, a refspec
  starting with `+`, `--no-verify`, or a refspec whose destination is `main`;
- `git commit` with `--no-verify` or `-n`;
- `git reset --hard`;
- `git branch -D`, or `git branch` with both a delete and a force flag.

Each denial SHALL name what to do instead. A command the guard cannot parse that contains `git`
or `gh` as a word SHALL produce a non-blocking hook error saying it was not checked. Every other
command SHALL get no output from the guard. This repository's `.claude/settings.json` SHALL declare no `permissions.deny` entry
that matches a guarded command.

#### Scenario: Guarded command in an adopted consumer
- **WHEN** the plugin's `PreToolUse` `Bash` hooks run with a project directory that carries `.github/workflows/agent-process.yml` and no copy of the guard, for each guarded command, alone and after `cd x &&`, under `sh -c`, after `A=1` and `env A=1`, and with `git -C .` or `gh -R o/r` before the subcommand
- **THEN** the call is denied and the reason names the alternative

#### Scenario: Ordinary git command
- **WHEN** the guard runs for an unparseable command without `git` or `gh`, `git push -u origin feature`, `git push origin HEAD`, `git branch -d feature`, `git reset --soft HEAD~1`, `git commit -m "skip --no-verify"`, or `gh pr view 1`
- **THEN** it exits 0 with no output

#### Scenario: Unparsed git command
- **WHEN** the guard runs for a command with an unbalanced quote that contains `git`, such as a heredoc commit whose body has an apostrophe
- **THEN** it exits 1 with `not checked` on stderr and no stdout, so the call proceeds and the hook error is visible

#### Scenario: Repository settings carry no guard deny
- **WHEN** the publisher tests read this repository's `.claude/settings.json`
- **THEN** no `permissions.deny` entry matches a guarded command, so the guard's reason reaches the agent
