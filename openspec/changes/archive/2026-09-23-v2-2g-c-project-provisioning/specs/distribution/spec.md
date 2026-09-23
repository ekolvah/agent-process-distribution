## ADDED Requirements

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
The plan of a dry-run and of a confirmed run SHALL print, as `manual`, setting the Project's
visibility and checking the template's built-in workflows, and `init` SHALL issue no command
that changes either.

#### Scenario: Manual actions
- **WHEN** a dry-run or confirmed run completes
- **THEN** its output carries the two `manual` rows and no command it issued changes a Project's visibility or workflows

## RENAMED Requirements

- FROM: `### Requirement: Local installation writes nothing remote`
- TO: `### Requirement: Init writes only the Project remotely`

## MODIFIED Requirements

### Requirement: Init writes only the Project remotely
A confirmed run's only GitHub writes SHALL be one copy of the template Project and one link
of a Project to the repository. The installer SHALL NOT create, update, or delete a ruleset,
branch protection, required check, secret, Project field or Status, or a workflow on the
default branch, and SHALL NOT commit or push in the consumer repository. A dry-run SHALL
issue no GitHub write.

#### Scenario: Confirmed run
- **WHEN** a confirmed run completes
- **THEN** every GitHub command it issued is a read, the Project copy, or the Project link, it has made no commit or push, and the consumer's changes are left uncommitted in its worktree

#### Scenario: Dry-run
- **WHEN** a dry-run completes
- **THEN** every GitHub command it issued is a read
