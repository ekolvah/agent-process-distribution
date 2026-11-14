## ADDED Requirements

### Requirement: Init runs the post-merge steps
A run SHALL read the PR whose head is the installation branch of its release, and, once that PR
reads `MERGED`, SHALL classify these transitions after the onboarding steps and a confirmed run
SHALL write them in this order: `protection`, `unchanged` when the default branch's rules
require both process checks, otherwise the ruleset *Protection activation observes quality
first* allows from that PR's head, and `conflict` naming the observation where it refuses;
and, with an agent account, `agent-collaborator`, the `push` invitation of the agent and its
acceptance with the agent's token, `unchanged` when that token's permission on the repository
is write or maintain; `agent-project`, the `WRITER` role of the agent on the linked Project,
`unchanged` when that token reads the Project's `viewerCanUpdate` true; `approval-ruleset`, the
shipped approval ruleset, converged as the process ruleset is; `auto-merge`, `unchanged` when
the repository's `allow_auto_merge` is true; `agent-token`, `env.GH_TOKEN` of the clone's
`.claude/settings.local.json` set to the agent's token, `unchanged` when *Install reports a
pending agent identity* reads it held, and `conflict` when git does not ignore that file or
it is not a JSON object; the run SHALL keep the file's other keys. After a ruleset write the run
SHALL read the ruleset back and exit non-zero unless it is the one planned: `protection` as
`activate_protection` reads it back, `approval-ruleset` by planning it again as `unchanged`. Before that PR reads `MERGED`, each transition not
`unchanged` SHALL print `after-merge` and SHALL NOT be written, and the body of the installation
PR SHALL list them as what its merge authorizes: the confirmed run that opens the PR writes them
into it, and a confirmed run that meets the PR open with another list rewrites its body with
`gh pr edit --body`. No line a run prints SHALL
carry the agent's token.

#### Scenario: Before the merge
- **WHEN** a confirmed run with an agent account opens the installation PR, in a repository with none of these states done
- **THEN** it prints `after-merge` for the six transitions, the PR's body lists them, and it issues none of their writes; a later confirmed run that meets the PR open with a changed list rewrites the body to it

#### Scenario: Upgrade with the steps done
- **WHEN** a dry-run meets an open upgrade PR in a repository whose post-merge states are all done
- **THEN** it prints each post-merge transition `unchanged` and no `after-merge` line

#### Scenario: After the merge
- **WHEN** a confirmed run with an agent account meets the merged installation PR whose head has both process checks green
- **THEN** it writes the six transitions in order, no output line carries the agent's token, and a rerun prints each `unchanged`

#### Scenario: Quality not observed
- **WHEN** a confirmed run meets the merged installation PR whose head has no successful `agent-review / agent-review` run
- **THEN** it prints `conflict protection` naming that observation, exits non-zero, and issues no post-merge write

#### Scenario: Token file not ignored
- **WHEN** a confirmed post-merge run meets a `.claude/settings.local.json` that git does not ignore, or that is not a JSON object
- **THEN** it prints `conflict agent-token` naming the reason, exits non-zero, and the file is unchanged

### Requirement: Init finds the agent account
The agent account SHALL be the github.com account `gh auth status`, run without `GH_TOKEN` and
`GITHUB_TOKEN`, lists besides its active one, the person. With several such accounts
`--agent <login>` SHALL choose one; without `--agent`, or with a login not among them, a
dry-run and a confirmed run SHALL print `conflict agent` naming them and exit non-zero before
any write. With none, the run SHALL have no agent account.

#### Scenario: Agent account
- **WHEN** `gh auth status` lists the person, active, and one other github.com account
- **THEN** the run's agent transitions name that account

#### Scenario: Several accounts
- **WHEN** `gh auth status` lists two github.com accounts besides the person and no `--agent` names one of them
- **THEN** the run prints `conflict agent` naming both, exits non-zero, and writes nothing

## MODIFIED Requirements

### Requirement: Init's remote writes are the Project and the installation PR
A confirmed run's only GitHub writes SHALL be one copy of the template Project, one link of a
Project to the repository, with `--area` the linked Project's `Area` options and area views as
*Init replaces the template's areas* states, the writes of *Init opens the installation
PR*: one issue, one push of the installation branch, one PR, and, in a repository with no
commits, one push of a commit with no files to the default branch, and the writes of *Init runs
the post-merge steps*. The installer SHALL NOT otherwise create, update, or delete a ruleset,
branch protection, required check, secret, collaborator, any other Project field, option or
role, Status, repository setting, or a workflow on the default branch, and SHALL NOT otherwise
commit to or push the default branch. A dry-run SHALL issue no GitHub write and SHALL make no
branch, commit, or push.

#### Scenario: Confirmed run
- **WHEN** a confirmed run without `--area` completes in a repository with commits, before the installation PR merges
- **THEN** every GitHub command it issued is a read, the Project copy, the Project link, the issue creation, or the PR creation, its only push is of the installation branch, and the default branch is unchanged locally and on `origin`

#### Scenario: Post-merge run
- **WHEN** a confirmed run with an agent account completes after the installation PR merged
- **THEN** every GitHub command it issued is a read or a write of *Init runs the post-merge steps*, and it made no push

#### Scenario: Dry-run
- **WHEN** a dry-run completes, with or without `--area` or an agent account
- **THEN** every GitHub command it issued is a read, and the consumer repository has no new branch, commit, or push

### Requirement: Install's admin steps run as the person
`activate_protection` and the post-merge transitions of `init` SHALL run each of their `gh`
calls without `GH_TOKEN` and `GITHUB_TOKEN` in its environment, except the calls that read
with or act as the agent account, which SHALL carry the agent's token as `GH_TOKEN`.

#### Scenario: A clone with the agent's identity
- **WHEN** `activate_protection`, or a confirmed post-merge run of `init`, runs with a `GH_TOKEN` in its environment
- **THEN** every `gh` call it issues runs without `GH_TOKEN` and `GITHUB_TOKEN`, except the acceptance of the invitation and the reads of the agent's permission and Project role, which carry the agent's token

### Requirement: Install reports a pending agent identity
Without an agent account, `init` SHALL print a `manual agent-identity` row unless this clone's
`.claude/settings.local.json` carries an `env.GH_TOKEN` whose permission on the repository,
read with that token in one `gh` call whatever the session's `GH_TOKEN`, is write or maintain.
The row SHALL name the permission read, or that no token is set, and Prepare's login of the
agent's bot account, then `init` again.

#### Scenario: Identity pending
- **WHEN** a run without an agent account meets a clone whose settings carry no `env.GH_TOKEN`, or a token whose permission on the repository is admin or read
- **THEN** its output carries one `manual agent-identity` row naming the permission or the missing token, and the fix

#### Scenario: Identity holds
- **WHEN** a run meets a clone whose settings carry a token with write permission on the repository
- **THEN** its output carries no `manual agent-identity` row, and the one `gh` call that carried that token as `GH_TOKEN` was a read

### Requirement: A Claude session start reports a missing agent identity
The installed skill check SHALL stay silent on the identity only when the session's `GH_TOKEN`
equals `env.GH_TOKEN` of the project's `.claude/settings.local.json`. Otherwise, including when
it cannot read that file, it SHALL exit 0 and add a `systemMessage` for the person and an
`additionalContext` for the agent. Each SHALL name `agent-process agent identity not set`, the
reason, and the fix: Install step 5 of the agent-process skill, then the restart of Claude Code.

#### Scenario: Identity missing
- **WHEN** a Claude session starts without `GH_TOKEN`, or with a `GH_TOKEN` that the project's settings do not hold
- **THEN** the check exits 0 and its output names `agent-process agent identity not set` and the fix, to the person and to the agent

#### Scenario: Identity set
- **WHEN** a Claude session starts with the `GH_TOKEN` of the project's settings
- **THEN** the check adds nothing for the identity

### Requirement: Install continues past the installation PR
The Install procedure of the shared skill SHALL, after the confirmed run opens the installation
PR, run `agent-process wait_for_pr <PR>`. On a first exit 3 it SHALL rerun once; a failing
`agent-process / quality` it SHALL fix by a commit on the PR and run it again; review threads and
any other failure, a second exit 3 included, it SHALL show the person, proposing a P0/P1 thread on
an installer-managed file as an issue in `ekolvah/agent-process-distribution`. Once the checks are
green it SHALL ask the person to merge; then, or on exit 4, it SHALL read
`gh pr view <PR> --json state`. On `MERGED` it SHALL, in the same session and without asking,
run step 5: `init --confirm` with the same arguments, then `gh auth setup-git`, then ask the
person to restart Claude Code when that run wrote `agent-token`; the merge is the consent. On any other state it SHALL show the person the state and stop
install.

#### Scenario: Installation PR merged
- **WHEN** the agent follows the skill's Install procedure and the installation PR it opened is merged
- **THEN** it runs `init --confirm` again without a new question, then `gh auth setup-git`, and asks the person at most to restart Claude Code

#### Scenario: Unasked upgrade PR merged
- **WHEN** the PR of a confirm run without asking is merged
- **THEN** the agent runs step 5, whose `init --confirm` prints each post-merge transition `unchanged`, and asks the person nothing

### Requirement: An upgrade's PR approval is its consent
The Install procedure of the shared skill SHALL, after showing a dry-run that exits 0, run
`--confirm` without asking: starting install is the consent to the run's writes outside the
PR, and the person's merge of the PR is the consent to its changes and to the post-merge run.
When that dry-run prints `approval-ruleset` and `auto-merge` `unchanged`, it SHALL then run `gh pr merge <PR> --auto --squash` on the PR the run opened and ask the person to
approve it. A dry-run that exits non-zero it SHALL show the person and SHALL NOT confirm.

#### Scenario: Upgrade with the agent's identity
- **WHEN** the dry-run exits 0 and prints `approval-ruleset` and `auto-merge` `unchanged`
- **THEN** the agent runs `--confirm` unasked, runs `gh pr merge <PR> --auto --squash` on the PR it opened, and asks the person to approve it

#### Scenario: Write outside the PR or no agent identity
- **WHEN** the dry-run exits 0 and plans a `project-copy`, `project-link`, `pre-push`, `project-areas` or `task-readings-*` transition, prints `approval-ruleset` or `auto-merge` other than `unchanged`, or prints a `manual agent-identity` row
- **THEN** the agent runs `--confirm` without asking and asks the person only to merge the PR it opened

#### Scenario: Dry-run conflict
- **WHEN** the dry-run exits non-zero
- **THEN** the agent shows its output to the person and does not run `--confirm`

## REMOVED Requirements

### Requirement: Install reports inactive protection
**Reason**: the `protection` transition of *Init runs the post-merge steps* activates it.
**Migration**: none; a run before the merge prints `after-merge protection` instead of the row.

### Requirement: Install reports disallowed auto-merge
**Reason**: the `auto-merge` transition of *Init runs the post-merge steps* allows it.
**Migration**: none; with an agent account a run before the merge prints `after-merge auto-merge`, without one the `manual agent-identity` row stands for it.
