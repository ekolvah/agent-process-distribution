## MODIFIED Requirements

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
